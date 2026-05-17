"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Float,
  ContactShadows,
  PerspectiveCamera,
} from "@react-three/drei";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/**
 * Hero 3D scene: a slowly turning, marble + gold scale of justice.
 *
 * Accepts a `tilt` prop in [-1, 1] which rotates the cross-beam (and
 * hangs the pans) so the user can physically weigh "bear vs bull" via
 * a slider outside the canvas. Rendered client-only (parent uses
 * dynamic({ ssr: false })) so three.js never reaches the server bundle.
 *
 * Geometry is hand-built from primitives — cylinders, torus, cones — so
 * we ship zero GLTF assets, ~150 KB of three.js but no model weight.
 */
export default function HeroScene({ tilt = 0 }: { tilt?: number }) {
  // IntersectionObserver gate — the canvas only mounts (and the
  // three.js renderer / WebGL context only initialises) when this
  // container actually enters the viewport. The hero is at the top
  // of the page so the gate trips immediately on landing, but a
  // visitor who arrives via a deep link further down the page never
  // pays the WebGL initialisation cost until they scroll back up.
  const gateRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!gateRef.current) return;
    const el = gateRef.current;
    // Use one observer for both "first mount" (rootMargin 200px =
    // trip while still scrolling up to it) and "currently visible"
    // (used to pause useFrame downstream).
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) setMounted(true);
        setVisible(e.isIntersecting);
      },
      { rootMargin: "200px 0px 200px 0px", threshold: 0 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={gateRef} className="h-full w-full">
      {mounted ? (
        <Canvas
          className="!h-full !w-full"
          // Recommendation A: cap pixel ratio at 1.5×. On retina/4K
          // this halves GPU bandwidth vs the previous [1, 2] cap.
          dpr={[1, 1.5]}
          // Recommendation E: pause the render loop when scrolled
          // off-screen. `frameloop` is reactive in R3F v8+ — flipping
          // it between "always" and "demand" stops the per-frame GPU
          // work while we're not on the hero.
          frameloop={visible ? "always" : "demand"}
          gl={{ antialias: true, alpha: true }}
        >
          {/* Camera pulled back to give the entire monument breathing room. */}
          <PerspectiveCamera makeDefault position={[0, 0.4, 7.2]} fov={30} />

          {/* dramatic three-point lighting (museum vitrine vibe) */}
          <ambientLight intensity={0.2} />
          <spotLight
            position={[4, 6, 3]}
            angle={0.45}
            penumbra={0.8}
            intensity={5}
            color="#f4ead3"
            castShadow
          />
          <pointLight position={[-3, 2, -2]} intensity={0.9} color="#d4a85e" />
          <pointLight position={[0, -2, 3]} intensity={0.35} color="#8a6da3" />

          <Suspense fallback={null}>
            <Float
              speed={0.8}
              rotationIntensity={0.2}
              floatIntensity={0.5}
              floatingRange={[-0.06, 0.06]}
            >
              <Scale tilt={tilt} />
            </Float>

            {/* Recommendation C (modified): procedural RoomEnvironment
                via PMREM. Keeps real cubemap-driven reflections but
                without the multi-megabyte warehouse HDR download. */}
            <ProceduralEnv />
            <ContactShadows
              position={[0, -2.2, 0]}
              opacity={0.45}
              scale={7}
              blur={2.6}
              far={3}
            />
          </Suspense>
        </Canvas>
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <div className="display text-[10px] uppercase tracking-[0.45em] text-muted-foreground/40">
            sculpting…
          </div>
        </div>
      )}
    </div>
  );
}

function ProceduralEnv() {
  // Generate a small procedural cubemap (PMREM-prefiltered RoomEnvironment)
  // once on mount. ~256×256 effective resolution. Visually similar to
  // a stripped-down warehouse preset — keeps gold + marble reflective
  // without downloading any HDR file.
  const { scene, gl } = useThree();
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    pmrem.compileCubemapShader();
    const env = new RoomEnvironment();
    const target = pmrem.fromScene(env, 0.04);
    const prev = scene.environment;
    scene.environment = target.texture;
    return () => {
      scene.environment = prev;
      target.dispose();
      pmrem.dispose();
    };
  }, [scene, gl]);
  return null;
}

function Scale({ tilt }: { tilt: number }) {
  const root = useRef<THREE.Group>(null!);
  const beam = useRef<THREE.Group>(null!);
  const leftPan = useRef<THREE.Group>(null!);
  const rightPan = useRef<THREE.Group>(null!);

  useFrame((_, dt) => {
    if (root.current) root.current.rotation.y += dt * 0.12;

    // Smoothly ease the beam toward the requested tilt.
    const target = tilt * 0.28; // max ±0.28 rad ≈ 16°
    if (beam.current) {
      beam.current.rotation.z += (target - beam.current.rotation.z) * 0.08;
    }

    // Pans rise / fall opposite to beam tilt so they stay below the beam ends.
    const beamRotZ = beam.current ? beam.current.rotation.z : 0;
    const drop = 0.65;
    const leftX = -1.25 * Math.cos(beamRotZ);
    const leftY = 0.95 + -1.25 * Math.sin(beamRotZ) - drop;
    const rightX = 1.25 * Math.cos(beamRotZ);
    const rightY = 0.95 + 1.25 * Math.sin(beamRotZ) - drop;
    if (leftPan.current) leftPan.current.position.set(leftX, leftY, 0);
    if (rightPan.current) rightPan.current.position.set(rightX, rightY, 0);
  });

  const marble = (
    <meshStandardMaterial
      color="#efe6cf"
      roughness={0.4}
      metalness={0.15}
      envMapIntensity={1.2}
    />
  );
  const gold = (
    <meshStandardMaterial
      color="#d4a85e"
      roughness={0.25}
      metalness={0.85}
      envMapIntensity={1.4}
    />
  );

  return (
    <group ref={root} position={[0, -0.25, 0]} scale={0.85}>
      {/* pedestal — segments halved 32→16 (recommendation D) */}
      <mesh position={[0, -1.65, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.55, 0.7, 0.25, 16]} />
        {marble}
      </mesh>
      <mesh position={[0, -1.87, 0]}>
        <cylinderGeometry args={[0.75, 0.8, 0.18, 16]} />
        {marble}
      </mesh>

      {/* vertical post */}
      <mesh position={[0, -0.3, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.07, 2.5, 16]} />
        {marble}
      </mesh>

      {/* finial */}
      <mesh position={[0, 1.05, 0]} castShadow>
        <sphereGeometry args={[0.13, 16, 16]} />
        {gold}
      </mesh>

      {/* tilting beam group — rotates in z */}
      <group ref={beam} position={[0, 0.95, 0]}>
        <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.05, 0.05, 2.6, 16]} />
          {gold}
        </mesh>
        {/* beam end caps */}
        <mesh position={[1.3, 0, 0]} castShadow>
          <sphereGeometry args={[0.085, 16, 16]} />
          {gold}
        </mesh>
        <mesh position={[-1.3, 0, 0]} castShadow>
          <sphereGeometry args={[0.085, 16, 16]} />
          {gold}
        </mesh>
        {/* chains — hang straight down from the beam end caps */}
        <mesh position={[1.3, -0.35, 0]}>
          <cylinderGeometry args={[0.012, 0.012, 0.7, 8]} />
          {gold}
        </mesh>
        <mesh position={[-1.3, -0.35, 0]}>
          <cylinderGeometry args={[0.012, 0.012, 0.7, 8]} />
          {gold}
        </mesh>
      </group>

      {/* pans — independent groups so they don't rotate with the beam */}
      <group ref={leftPan}>
        <Pan />
      </group>
      <group ref={rightPan}>
        <Pan />
      </group>
    </group>
  );
}

function Pan() {
  return (
    <group>
      <mesh castShadow receiveShadow>
        {/* segments halved 32→16, torus ring 48→24 (recommendation D) */}
        <cylinderGeometry args={[0.5, 0.34, 0.08, 16, 1, false]} />
        <meshStandardMaterial
          color="#d4a85e"
          roughness={0.25}
          metalness={0.92}
          envMapIntensity={1.5}
        />
      </mesh>
      <mesh position={[0, 0.04, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.5, 0.014, 8, 24]} />
        <meshStandardMaterial color="#b88a3f" roughness={0.3} metalness={0.95} />
      </mesh>
    </group>
  );
}

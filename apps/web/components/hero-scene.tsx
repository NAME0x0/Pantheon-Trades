"use client";

import { Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  Environment,
  Float,
  ContactShadows,
  PerspectiveCamera,
} from "@react-three/drei";
import * as THREE from "three";

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
  return (
    <Canvas
      className="!h-full !w-full"
      dpr={[1, 2]}
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

        <Environment preset="warehouse" />
        <ContactShadows
          position={[0, -2.2, 0]}
          opacity={0.45}
          scale={7}
          blur={2.6}
          far={3}
        />
      </Suspense>
    </Canvas>
  );
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
      {/* pedestal */}
      <mesh position={[0, -1.65, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.55, 0.7, 0.25, 32]} />
        {marble}
      </mesh>
      <mesh position={[0, -1.87, 0]}>
        <cylinderGeometry args={[0.75, 0.8, 0.18, 32]} />
        {marble}
      </mesh>

      {/* vertical post */}
      <mesh position={[0, -0.3, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.07, 2.5, 24]} />
        {marble}
      </mesh>

      {/* finial */}
      <mesh position={[0, 1.05, 0]} castShadow>
        <sphereGeometry args={[0.13, 32, 32]} />
        {gold}
      </mesh>

      {/* tilting beam group — rotates in z */}
      <group ref={beam} position={[0, 0.95, 0]}>
        <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.05, 0.05, 2.6, 24]} />
          {gold}
        </mesh>
        {/* beam end caps */}
        <mesh position={[1.3, 0, 0]} castShadow>
          <sphereGeometry args={[0.085, 24, 24]} />
          {gold}
        </mesh>
        <mesh position={[-1.3, 0, 0]} castShadow>
          <sphereGeometry args={[0.085, 24, 24]} />
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
        <cylinderGeometry args={[0.5, 0.34, 0.08, 32, 1, false]} />
        <meshStandardMaterial
          color="#d4a85e"
          roughness={0.25}
          metalness={0.92}
          envMapIntensity={1.5}
        />
      </mesh>
      <mesh position={[0, 0.04, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.5, 0.014, 12, 48]} />
        <meshStandardMaterial color="#b88a3f" roughness={0.3} metalness={0.95} />
      </mesh>
    </group>
  );
}

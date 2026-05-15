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
 * Hero 3D scene: a slowly turning, marble-textured scale of justice.
 * Rendered client-only (dynamic({ ssr: false }) in the parent) to avoid
 * shipping three.js to the server bundle.
 *
 * Geometry is hand-built from primitives — cylinders, torus, cones — so
 * we ship zero GLTF assets. ~150 KB of three.js but no model weight.
 */
export default function HeroScene() {
  return (
    <Canvas
      className="!h-full !w-full"
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      <PerspectiveCamera makeDefault position={[0, 0.3, 5.2]} fov={32} />

      {/* dramatic three-point lighting (museum vitrine vibe) */}
      <ambientLight intensity={0.18} />
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
          speed={0.9}
          rotationIntensity={0.3}
          floatIntensity={0.6}
          floatingRange={[-0.08, 0.08]}
        >
          <Scale />
        </Float>

        <Environment preset="warehouse" />
        <ContactShadows
          position={[0, -1.85, 0]}
          opacity={0.45}
          scale={6}
          blur={2.6}
          far={3}
        />
      </Suspense>
    </Canvas>
  );
}

function Scale() {
  const root = useRef<THREE.Group>(null!);
  useFrame((_, dt) => {
    if (root.current) {
      root.current.rotation.y += dt * 0.15;
    }
  });

  // Marble material — bright, slightly rough, subtle envmap pickup
  const marble = (
    <meshStandardMaterial
      color="#efe6cf"
      roughness={0.4}
      metalness={0.15}
      envMapIntensity={1.2}
    />
  );
  // Gold for the beam + chains
  const gold = (
    <meshStandardMaterial
      color="#d4a85e"
      roughness={0.25}
      metalness={0.85}
      envMapIntensity={1.4}
    />
  );

  return (
    <group ref={root} position={[0, -0.2, 0]}>
      {/* pedestal */}
      <mesh position={[0, -1.4, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.55, 0.7, 0.25, 32]} />
        {marble}
      </mesh>
      <mesh position={[0, -1.62, 0]}>
        <cylinderGeometry args={[0.75, 0.8, 0.18, 32]} />
        {marble}
      </mesh>

      {/* vertical post */}
      <mesh position={[0, -0.1, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.07, 2.4, 24]} />
        {marble}
      </mesh>
      {/* finial */}
      <mesh position={[0, 1.18, 0]} castShadow>
        <sphereGeometry args={[0.12, 32, 32]} />
        {gold}
      </mesh>

      {/* cross beam */}
      <mesh position={[0, 0.95, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.05, 0.05, 2.6, 24]} />
        {gold}
      </mesh>
      {/* beam end caps */}
      <mesh position={[1.3, 0.95, 0]} castShadow>
        <sphereGeometry args={[0.08, 24, 24]} />
        {gold}
      </mesh>
      <mesh position={[-1.3, 0.95, 0]} castShadow>
        <sphereGeometry args={[0.08, 24, 24]} />
        {gold}
      </mesh>

      {/* chains (slim cylinders) */}
      <mesh position={[1.3, 0.55, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 0.8, 8]} />
        {gold}
      </mesh>
      <mesh position={[-1.3, 0.55, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 0.8, 8]} />
        {gold}
      </mesh>

      {/* pans — shallow cones */}
      <Pan position={[1.3, 0.05, 0]} />
      <Pan position={[-1.3, 0.05, 0]} />
    </group>
  );
}

function Pan({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* dish */}
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[0.45, 0.32, 0.08, 32, 1, false]} />
        <meshStandardMaterial
          color="#d4a85e"
          roughness={0.25}
          metalness={0.92}
          envMapIntensity={1.5}
        />
      </mesh>
      {/* rim (slim torus for depth) */}
      <mesh position={[0, 0.04, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.45, 0.012, 12, 48]} />
        <meshStandardMaterial color="#b88a3f" roughness={0.3} metalness={0.95} />
      </mesh>
    </group>
  );
}

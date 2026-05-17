"use client";

import { motion, useInView, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Reveals child once the wrapper is in view. Default: rise + fade,
 * 0.7s out, slight stagger via `delay` prop.
 */
export function Reveal({
  children,
  delay = 0,
  className,
  y = 24,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  y?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px -10% 0px" });
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </motion.div>
  );
}

/** Animated odometer-style integer counter. */
export function Counter({
  to,
  duration = 2.2,
  className,
  format = (n) => Math.floor(n).toLocaleString(),
}: {
  to: number;
  duration?: number;
  className?: string;
  format?: (n: number) => string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-20% 0px" });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { duration: duration * 1000, bounce: 0 });
  const display = useTransform(spring, (latest) => format(latest));

  useEffect(() => {
    if (inView) mv.set(to);
  }, [inView, to, mv]);

  return (
    <motion.span ref={ref} className={className}>
      {display}
    </motion.span>
  );
}

/**
 * Typewriter that scrubs through a hex string character by character.
 * Used for the on-chain restraint tx hash to give the visitor a sense
 * of "this is being written, live."
 */
export function Typewriter({
  text,
  speed = 22,
  className,
  startWhenInView = true,
}: {
  text: string;
  speed?: number;
  className?: string;
  startWhenInView?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (startWhenInView && !inView) return;
    if (shown >= text.length) return;
    const id = setTimeout(() => setShown((s) => s + 1), speed);
    return () => clearTimeout(id);
  }, [inView, shown, text.length, speed, startWhenInView]);

  return (
    <span ref={ref} className={cn("mono", className)}>
      {text.slice(0, shown)}
      <span
        aria-hidden
        className={cn(
          "ml-0.5 inline-block h-[1em] w-[2px] -translate-y-[1px] bg-primary align-middle",
          shown < text.length ? "animate-pulse" : "opacity-0"
        )}
      />
    </span>
  );
}

/** Marquee that scrolls children left, infinite loop. CSS-only. */
export function Marquee({
  children,
  speed = 38,
  className,
}: {
  children: React.ReactNode;
  speed?: number;
  className?: string;
}) {
  return (
    <div className={cn("relative overflow-hidden", className)}>
      <div
        className="flex gap-12 whitespace-nowrap"
        style={{ animation: `pantheon-marquee ${speed}s linear infinite` }}
      >
        <div className="flex shrink-0 gap-12">{children}</div>
        <div aria-hidden className="flex shrink-0 gap-12">
          {children}
        </div>
      </div>
      {/* keyframes live in styles/globals.css */}
    </div>
  );
}

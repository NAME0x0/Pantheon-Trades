"use client";

import { motion, useInView, useMotionValue, useSpring, useTransform } from "framer-motion";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";

/* ─── Shared IntersectionObserver for Reveal ─────────────────────────
 *
 * Recommendation H: the home page mounts ~85 Reveal instances. Before
 * this change each one ran its own framer-motion observer + spring,
 * producing a 200-400 ms hitch on first paint. This provider exposes
 * a single IntersectionObserver shared across every Reveal child.
 * Each child registers a callback; the observer fires it once when
 * the element scrolls into view and then unobserves.
 *
 * The actual "rise + fade" animation is now plain CSS — see the
 * .reveal / .reveal-in classes in styles/globals.css. CSS transitions
 * are GPU-composited and free at the per-frame level.
 *
 * Components that want the old framer-motion behaviour can opt back
 * in by importing motion directly; this just replaces the default
 * Reveal export.
 */

type RevealCallback = () => void;

interface RevealCtxValue {
  observe: (el: Element, cb: RevealCallback) => () => void;
}

const RevealCtx = createContext<RevealCtxValue | null>(null);

export function RevealProvider({ children }: { children: React.ReactNode }) {
  const callbacks = useRef<Map<Element, RevealCallback>>(new Map());
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const cbs = callbacks.current;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          const cb = cbs.get(e.target);
          if (cb) {
            cb();
            cbs.delete(e.target);
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "-10% 0px -10% 0px", threshold: 0 },
    );
    observerRef.current = io;
    return () => {
      io.disconnect();
      observerRef.current = null;
      cbs.clear();
    };
  }, []);

  const observe = useCallback((el: Element, cb: RevealCallback) => {
    callbacks.current.set(el, cb);
    observerRef.current?.observe(el);
    return () => {
      callbacks.current.delete(el);
      observerRef.current?.unobserve(el);
    };
  }, []);

  const value = useMemo(() => ({ observe }), [observe]);
  return <RevealCtx.Provider value={value}>{children}</RevealCtx.Provider>;
}

/**
 * Reveals child once the wrapper is in view. Default: rise + fade,
 * 0.85 s out, slight stagger via `delay` prop.
 *
 * Uses the shared RevealProvider observer when available; falls back
 * to its own IntersectionObserver if a caller forgot to wrap their
 * tree (so we never silently break).
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
  const [visible, setVisible] = useState(false);
  const ctx = useContext(RevealCtx);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    if (ctx) {
      return ctx.observe(el, () => setVisible(true));
    }
    // Fallback: standalone observer if no provider.
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin: "-10% 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ctx]);

  const style = {
    "--reveal-y": `${y}px`,
    "--reveal-delay": `${delay}s`,
  } as React.CSSProperties;

  return (
    <div
      ref={ref}
      className={cn("reveal", visible && "reveal-in", className)}
      style={style}
    >
      {children}
    </div>
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

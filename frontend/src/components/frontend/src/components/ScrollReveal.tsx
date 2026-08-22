import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface ScrollRevealProps {
  children: ReactNode;
  delay?: number;
  className?: string;
  direction?: "up" | "left" | "right";
}

const offsets = {
  up: { y: 60, x: 0 },
  left: { y: 0, x: -60 },
  right: { y: 0, x: 60 },
};

const ScrollReveal = ({
  children,
  delay = 0,
  className = "",
  direction = "up",
}: ScrollRevealProps) => {
  const { x, y } = offsets[direction];

  return (
    <motion.div
      initial={{ opacity: 0, rotateX: 15, x, y }}
      whileInView={{ opacity: 1, rotateX: 0, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      style={{ perspective: 1000, transformStyle: "preserve-3d" }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

export default ScrollReveal;

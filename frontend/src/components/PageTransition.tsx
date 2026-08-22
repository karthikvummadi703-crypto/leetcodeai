import { motion } from "framer-motion";
import type { ReactNode } from "react";

const pageVariants = {
  initial: { opacity: 0, rotateY: -10, scale: 0.96 },
  animate: { opacity: 1, rotateY: 0, scale: 1 },
  exit: { opacity: 0, rotateY: 10, scale: 0.96 },
};

const pageTransition = {
  type: "spring" as const,
  stiffness: 260,
  damping: 26,
  mass: 0.9,
};

const PageTransition = ({ children }: { children: ReactNode }) => (
  <motion.div
    initial="initial"
    animate="animate"
    exit="exit"
    variants={pageVariants}
    transition={pageTransition}
    style={{
      perspective: 1200,
      transformStyle: "preserve-3d",
      willChange: "transform, opacity",
    }}
    className="min-h-screen"
  >
    {children}
  </motion.div>
);

export default PageTransition;

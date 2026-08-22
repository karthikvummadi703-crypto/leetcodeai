import { motion } from "framer-motion";
import type { ReactNode } from "react";

const pageVariants = {
  initial: { opacity: 0, rotateX: 14, y: 40 },
  animate: { opacity: 1, rotateX: 0, y: 0 },
  exit: { opacity: 0, rotateX: -10, y: -24 },
};

const pageTransition = {
  duration: 0.55,
  ease: [0.16, 1, 0.3, 1] as const,
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
      transformOrigin: "top center",
      willChange: "transform, opacity",
    }}
    className="min-h-screen"
  >
    {children}
  </motion.div>
);

export default PageTransition;

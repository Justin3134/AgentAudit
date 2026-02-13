import { motion } from "framer-motion";

const Hero = () => {
  return (
    <section className="min-h-[90vh] flex items-center relative">
      <div className="max-w-6xl mx-auto px-6 lg:px-8 pt-32 pb-24">
        <div className="max-w-3xl">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-sm font-medium tracking-widest uppercase text-muted-foreground mb-6"
          >
            Execution‑Time Authorization
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[1.1] tracking-tight text-foreground mb-8"
          >
            Security Controls
            <br />
            For Agents
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg md:text-xl text-muted-foreground leading-relaxed mb-10 max-w-2xl"
          >
            Cryptographically prove a real human approved a specific action at execution time
            across agentic AI, hardware systems, and high‑risk enterprise and infrastructure workflows.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 items-start"
          >
            <a
              href="https://calendly.com/ben-qsva/30min"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-7 py-3.5 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-foreground/90 transition-colors"
            >
              Talk to the QSVA Team
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="ml-2">
                <path d="M3 8h10m0 0L9 4m4 4L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </a>
            <span className="text-sm text-muted-foreground italic self-center">
              Now working with select design partners
            </span>
          </motion.div>
        </div>
      </div>

      {/* Subtle decorative line */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-border" />
    </section>
  );
};

export default Hero;

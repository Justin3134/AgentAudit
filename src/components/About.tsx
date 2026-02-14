import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const About = () => {
  return (
    <section id="about" className="py-20 md:py-28 relative">
      {/* Decorative vertical line */}
      <div className="absolute top-0 left-1/2 w-px h-24 bg-gradient-to-b from-transparent to-border hidden md:block" />

      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        {/* Intro */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
          className="max-w-3xl mb-16"
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="h-px w-8 bg-foreground" />
            <span className="text-xs font-medium tracking-[0.2em] uppercase text-muted-foreground">The Problem</span>
          </div>
          <h2 className="font-serif text-4xl md:text-5xl text-foreground mb-8">
            About QSVA
          </h2>
          <div className="space-y-5 text-muted-foreground leading-relaxed text-base md:text-lg">
            <p>
              Agentic systems don't just execute commands — they decide what actions to take.
              They initiate financial transfers, modify infrastructure, recover systems, and act
              across distributed environments without continuous human supervision.
            </p>
            <p>
              IAM, MFA, and device trust were designed for human‑initiated sessions, not for systems
              that generate intent and execute actions autonomously. As agentic systems scale, the
              question is no longer <em className="text-foreground not-italic font-medium">who logged in</em> — it's{" "}
              <em className="text-foreground not-italic font-medium">who approved this specific action at the moment it executed</em>.
            </p>
          </div>
        </motion.div>

        {/* Callout */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
          className="border-l-2 border-foreground pl-8 py-2 max-w-3xl"
        >
          <p className="font-serif text-xl md:text-2xl text-foreground leading-relaxed italic">
            "QSVA does not replace autonomy.
            It defines the boundary where autonomy must stop."
          </p>
        </motion.div>

        {/* Learn More link */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-12"
        >
          <Link
            to="/about"
            className="group inline-flex items-center text-sm font-medium text-foreground underline underline-offset-4 decoration-border hover:decoration-foreground transition-colors"
          >
            Read the full QSVA thesis
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="ml-2 transition-transform duration-300 group-hover:translate-x-1">
              <path d="M3 8h10m0 0L9 4m4 4L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>
        </motion.div>
      </div>
    </section>
  );
};

export default About;

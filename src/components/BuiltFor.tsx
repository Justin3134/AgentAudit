import { motion } from "framer-motion";

const items = [
  {
    title: "Agentic AI Platforms",
    desc: "Automated systems and orchestration layers executing autonomous workflows.",
  },
  {
    title: "AI Hardware & Edge",
    desc: "Cyber‑physical environments and edge computing where actions are irreversible.",
  },
  {
    title: "Financial Systems",
    desc: "Payment infrastructure and financial execution requiring human authorization.",
  },
  {
    title: "Government & Defense",
    desc: "Critical infrastructure and mission‑critical systems demanding accountability.",
  },
  {
    title: "Enterprise Security",
    desc: "High‑risk actions beyond IAM that need execution‑time trust verification.",
  },
];

const BuiltFor = () => {
  return (
    <section id="built-for" className="py-24 md:py-32 bg-secondary">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="mb-16"
        >
          <h2 className="font-serif text-4xl md:text-5xl text-foreground mb-4">
            Built For
          </h2>
          <p className="text-muted-foreground text-lg max-w-xl">
            QSVA is built for teams accountable for execution risk across critical systems.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border rounded-lg overflow-hidden">
          {items.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="bg-background p-8 lg:p-10"
            >
              <span className="text-xs font-medium tracking-widest uppercase text-muted-foreground mb-4 block">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="text-lg font-semibold text-foreground mb-2">{item.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-12 text-center"
        >
          <a
            href="https://calendly.com/ben-qsva/30min"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-foreground underline underline-offset-4 decoration-border hover:decoration-foreground transition-colors"
          >
            Talk to the QSVA Team →
          </a>
        </motion.div>
      </div>
    </section>
  );
};

export default BuiltFor;

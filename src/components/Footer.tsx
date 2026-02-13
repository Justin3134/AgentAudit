import { Linkedin } from "lucide-react";

const Footer = () => {
  return (
    <footer className="py-24 md:py-32">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        {/* CTA */}
        <div className="text-center mb-20">
          <h2 className="font-serif text-3xl md:text-4xl text-foreground mb-5">
            Ready to secure agentic execution?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto leading-relaxed">
            Talk to the QSVA team about bringing execution‑time trust to your autonomous systems.
          </p>
          <a
            href="https://calendly.com/ben-qsva/30min"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-7 py-3.5 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-foreground/90 transition-colors"
          >
            Schedule a Conversation
          </a>
        </div>

        {/* Bottom */}
        <div className="border-t border-border pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <span className="text-sm text-muted-foreground">© 2026 QSVA. All rights reserved.</span>
          <a
            href="https://www.linkedin.com/company/qsva"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <Linkedin size={18} />
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

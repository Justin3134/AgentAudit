import { Linkedin } from "lucide-react";

const Footer = () => {
  return (
    <footer className="py-24 md:py-32">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
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

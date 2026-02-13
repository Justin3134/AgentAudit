import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";

const navLinks = [
  { label: "Built For", href: "#built-for" },
  { label: "About", href: "#about" },
  { label: "Team", href: "#team" },
];

const QSVALogo = ({ className = "" }: { className?: string }) => (
  <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Outer hexagon */}
    <polygon points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" stroke="currentColor" strokeWidth="2.5" fill="none" />
    {/* Inner hexagon */}
    <polygon points="50,22 73,36 73,64 50,78 27,64 27,36" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.6" />
    {/* Center lines connecting inner to outer - cube effect */}
    <line x1="50" y1="5" x2="50" y2="22" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
    <line x1="90" y1="72.5" x2="73" y2="64" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
    <line x1="10" y1="72.5" x2="27" y2="64" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
  </svg>
);

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleClick = (href: string) => {
    setMobileOpen(false);
    document.querySelector(href)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <motion.nav
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-background/90 backdrop-blur-md border-b border-border" : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 lg:px-8 py-5 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2.5" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <QSVALogo className="text-foreground" />
          <span className="text-lg font-semibold tracking-wide text-foreground">QSVA</span>
        </a>

        <div className="hidden md:flex items-center gap-10">
          {navLinks.map((link) => (
            <button
              key={link.href}
              onClick={() => handleClick(link.href)}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {link.label}
            </button>
          ))}
          <a
            href="https://calendly.com/ben-qsva/30min"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium px-5 py-2 rounded-md bg-primary text-primary-foreground hover:bg-foreground/90 transition-colors"
          >
            Contact
          </a>
        </div>

        <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-foreground">
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="md:hidden bg-background border-b border-border px-6 pb-6 space-y-3"
        >
          {navLinks.map((link) => (
            <button
              key={link.href}
              onClick={() => handleClick(link.href)}
              className="block w-full text-left text-sm text-muted-foreground hover:text-foreground py-2"
            >
              {link.label}
            </button>
          ))}
          <a
            href="https://calendly.com/ben-qsva/30min"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-center text-sm font-medium px-5 py-2.5 rounded-md bg-primary text-primary-foreground"
          >
            Contact
          </a>
        </motion.div>
      )}
    </motion.nav>
  );
};

export default Navbar;

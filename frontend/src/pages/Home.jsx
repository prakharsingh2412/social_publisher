import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

// --- IMPORT YOUR LOGOS HERE ---
import twitterLogo from '../assets/twitter.png'; 
import instagramLogo from '../assets/instagram.png';
import facebookLogo from '../assets/facebook.png';
import youtubeLogo from '../assets/youtube.png';

// --- Platform Data ---
const PLATFORMS = [
  { id: 'twitter', name: 'Twitter / X', icon: twitterLogo, bg: 'bg-blue-50' },
  { id: 'instagram', name: 'Instagram', icon: instagramLogo, bg: 'bg-pink-50' },
  { id: 'facebook', name: 'Facebook', icon: facebookLogo, bg: 'bg-indigo-50' },
  { id: 'youtube', name: 'YouTube', icon: youtubeLogo, bg: 'bg-red-50' },
];

// --- 3D Card Shuffle Component ---
function PlatformShuffle() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % PLATFORMS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative flex h-[400px] w-full items-center justify-center perspective-[1000px]">
      <div className="absolute h-64 w-64 rounded-full bg-brand-pink/20 blur-[80px]" />

      {PLATFORMS.map((platform, index) => {
        const offset = (index - activeIndex + PLATFORMS.length) % PLATFORMS.length;
        const isTop = offset === 0;

        return (
          <motion.div
            key={platform.id}
            initial={false}
            animate={{
              zIndex: PLATFORMS.length - offset,
              y: offset * 25,
              scale: 1 - offset * 0.05,
              rotateX: offset * 5,
              opacity: offset === 3 ? 0.5 : 1,
            }}
            transition={{ type: "spring", stiffness: 200, damping: 25 }}
            className="absolute flex w-72 flex-col items-center justify-center rounded-2xl border border-gray-100 bg-white p-8 shadow-xl shadow-brand-pink/5"
            style={{ transformStyle: 'preserve-3d' }}
          >
            <div className={`mb-6 flex h-20 w-20 items-center justify-center rounded-2xl p-3 shadow-sm ${platform.bg}`}>
              <img src={platform.icon} alt={`${platform.name} logo`} className="h-full w-full object-contain" />
            </div>
            
            <h3 className="text-xl font-bold text-brand-dark">{platform.name}</h3>
            <p className="mt-2 text-center text-sm text-gray-500">Ready to publish</p>

            {isTop && (
              <motion.div 
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: "100%", opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.8 }}
                className="mt-6 flex w-full items-center gap-2 rounded-lg bg-gray-50 p-3"
              >
                <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                <span className="text-xs font-semibold text-gray-600">Syncing Account...</span>
              </motion.div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

// --- Animation Variants ---
const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.2 } }
};

// --- Bent Card Component ---
function BentFeatureCard({ feature }) {
  return (
    <div className="relative flex h-full w-full items-center justify-center" style={{ perspective: '1200px' }}>
      <motion.div
        className="relative flex h-full w-full rounded-2xl border border-gray-100 bg-white shadow-xl shadow-brand-pink/15"
        initial={{ rotateY: 0, rotateX: 0 }}
        whileHover={{ 
          rotateY: -15, 
          rotateX: 5, 
          scale: 1.03, 
          boxShadow: "0 25px 50px -12px rgba(250, 0, 86, 0.3)" 
        }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        <div className="relative z-10 flex-1 overflow-hidden rounded-l-2xl bg-white p-8" style={{ transform: 'translateZ(20px)' }}>
          <div className="mb-4 text-4xl">{feature.icon}</div>
          <h3 className="mb-2 text-xl font-bold text-brand-dark">{feature.title}</h3>
          <p className="text-sm leading-relaxed text-gray-500">{feature.desc}</p>
        </div>
        
        <motion.div
          className="absolute bottom-0 right-0 top-0 z-0 w-10 origin-left overflow-hidden rounded-r-2xl bg-brand-pink"
          style={{
            transform: 'rotateY(50deg) translateZ(-1px)',
            backgroundImage: `linear-gradient(to bottom, rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(to right, rgba(255,255,255,0.3) 1px, transparent 1px)`,
            backgroundSize: '8px 8px',
            boxShadow: 'inset 4px 0 10px rgba(0,0,0,0.2)'
          }}
        >
          <div className="absolute inset-0 bg-gradient-to-l from-black/30 to-transparent" />
        </motion.div>
      </motion.div>
    </div>
  );
}

export default function Home() {
  const { hash } = useLocation(); // <-- Get the hash from the URL

  // --- SCROLL LOGIC ADDED HERE ---
  useEffect(() => {
    if (hash) {
      const element = document.getElementById(hash.replace('#', ''));
      if (element) {
        // Add a slight delay to ensure the page has rendered before scrolling
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      }
    }
  }, [hash]);

  const features = [
    { icon: '🔐', title: 'Secure OAuth', desc: 'Connect your accounts safely. Tokens are encrypted at rest and tied directly to your user profile.' },
    { icon: '🚀', title: 'Blazing Fast', desc: 'Powered by Django, Celery, and Redis for reliable, asynchronous publishing to all platforms.' },
    { icon: '📊', title: 'Unified Dashboard', desc: 'Track per-platform success and failure states from a single, clean interface.' }
  ];

  return (
    <div className="flex min-h-screen flex-col bg-brand-gray font-sans">
      <Navbar />
      
      <main className="flex-1">
        {/* ================= HERO SECTION ================= */}
        <section className="relative overflow-hidden px-6 pt-16 pb-24 md:pt-24 md:pb-32 bg-gradient-to-br from-white via-pink-50 to-brand-pink/10">
          <div className="mx-auto max-w-6xl">
            
            <div className="grid items-center gap-12 lg:grid-cols-[1.5fr_1fr]">
              
              {/* Left Side: Text Content */}
              <motion.div 
                initial="hidden" 
                animate="visible" 
                variants={staggerContainer}
                className="max-w-3xl"
              >
                <motion.div variants={fadeUp}>
                  <span className="mb-4 inline-block rounded-full bg-brand-pink/10 px-3 py-1 text-sm font-semibold text-brand-pink">
                    ✨ One post. Every platform.
                  </span>
                </motion.div>
                
                <motion.h1 variants={fadeUp} className="text-4xl font-bold tracking-tight text-brand-dark md:text-6xl lg:text-7xl">
                  Publish everywhere <br />
                  <span className="text-brand-pink">without the hassle.</span>
                </motion.h1>
                
                <motion.p variants={fadeUp} className="mt-6 max-w-2xl text-lg text-gray-600 md:text-xl">
                  Schedule and publish your content to YouTube, Facebook, Twitter/X, and Instagram simultaneously. 
                  Built securely with JWT and OAuth.
                </motion.p>
                
                <motion.div variants={fadeUp} className="mt-10 flex flex-wrap gap-4">
                  <Link to="/register" className="rounded-lg bg-brand-pink px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-pink/30 transition-transform hover:-translate-y-1 hover:bg-brand-pink/90">
                    Get started for free
                  </Link>
                  {/* Changed this to a Link tag so it uses React Router */}
                  <Link to="/#about" className="rounded-lg border border-gray-300 bg-white px-8 py-3.5 text-base font-semibold text-brand-dark transition-colors hover:bg-gray-50">
                    Learn more
                  </Link>
                </motion.div>
              </motion.div>

              {/* Right Side: Animated Card Stack */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="hidden lg:block"
              >
                <PlatformShuffle />
              </motion.div>

            </div>
          </div>
        </section>

        {/* ================= ABOUT SECTION ================= */}
        {/* Added scroll-mt-24 so the sticky navbar doesn't cover the heading */}
        <section id="about" className="bg-white px-6 py-24 scroll-mt-24">
          <div className="mx-auto max-w-6xl">
            <motion.div 
              initial="hidden" 
              whileInView="visible" 
              viewport={{ once: true, margin: "-100px" }}
              variants={fadeUp}
              className="mx-auto mb-16 max-w-2xl text-center"
            >
              <h2 className="text-3xl font-bold text-brand-dark md:text-4xl">Why use Social Publisher?</h2>
              <p className="mt-4 text-gray-500">We handle the complex OAuth flows and API limits so you can focus on creating great content.</p>
            </motion.div>

            <motion.div 
              initial="hidden" 
              whileInView="visible" 
              viewport={{ once: true }} 
              variants={staggerContainer}
              className="grid gap-8 md:grid-cols-3"
            >
              {features.map((feature, i) => (
                <motion.div key={i} variants={fadeUp}>
                  <BentFeatureCard feature={feature} />
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ================= CONTACT SECTION ================= */}
        {/* Added scroll-mt-24 here too */}
        <section id="contact" className="bg-brand-gray px-6 py-24 scroll-mt-24">
          <div className="mx-auto max-w-6xl">
            <motion.div 
              initial="hidden" 
              whileInView="visible" 
              viewport={{ once: true }}
              variants={fadeUp}
              className="grid items-center gap-12 md:grid-cols-2"
            >
              <div>
                <h2 className="text-3xl font-bold text-brand-dark md:text-4xl">Get in touch</h2>
                <p className="mb-8 mt-4 text-gray-500">
                  Have questions about the API, need enterprise access, or just want to say hi? Drop us a message.
                </p>
                <div className="space-y-4 text-sm font-medium text-brand-dark">
                  <p className="flex items-center gap-3"><span className="text-xl">📧</span> support@socialpublisher.com</p>
                  <p className="flex items-center gap-3"><span className="text-xl">📍</span> Remote / Worldwide</p>
                </div>
              </div>

              {/* Contact Form */}
              <form className="space-y-4 rounded-2xl border border-gray-100 bg-white p-8 shadow-sm" onSubmit={(e) => e.preventDefault()}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
                    <input type="text" placeholder="Jane Doe" className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20" />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                    <input type="email" placeholder="jane@example.com" className="w-full rounded-lg border border-gray-300 px-4 py-2.5 focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20" />
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Message</label>
                  <textarea rows="4" placeholder="How can we help?" className="w-full resize-none rounded-lg border border-gray-300 px-4 py-2.5 focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"></textarea>
                </div>
                <button className="w-full rounded-lg bg-brand-dark px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-black">
                  Send Message
                </button>
              </form>
            </motion.div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
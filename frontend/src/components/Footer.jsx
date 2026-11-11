import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="bg-brand-dark text-white/70">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link to="/" className="text-xl font-bold text-white">
              📣 Social Publisher
            </Link>
            <p className="mt-4 max-w-sm text-sm">
              Schedule and publish content to YouTube, Facebook, Twitter/X, and Instagram from a single API. 
              Built for creators and teams.
            </p>
          </div>

          {/* Links */}
          <div>
            <h3 className="font-semibold text-white">Product</h3>
            <ul className="mt-4 space-y-2 text-sm">
              {/* Changed to Link */}
              <li><Link to="/#about" className="hover:text-brand-pink transition-colors">Features</Link></li>
              <li><Link to="/#contact" className="hover:text-brand-pink transition-colors">Contact</Link></li>
              <li><Link to="/login" className="hover:text-brand-pink transition-colors">Sign in</Link></li>
              <li><Link to="/register" className="hover:text-brand-pink transition-colors">Create account</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-semibold text-white">Legal</h3>
            <ul className="mt-4 space-y-2 text-sm">
              <li><a href="#" className="hover:text-brand-pink transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-brand-pink transition-colors">Terms of Service</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between border-t border-white/10 pt-6 text-xs md:flex-row">
          <p>&copy; {new Date().getFullYear()} Social Publisher. All rights reserved.</p>
          <p className="mt-2 md:mt-0">Built with React & Django</p>
        </div>
      </div>
    </footer>
  );
}
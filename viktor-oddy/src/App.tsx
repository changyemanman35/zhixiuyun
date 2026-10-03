import HeroVex from './components/HeroVex'
import Marquee from './components/Marquee'
import Testimonial from './components/Testimonial'
import Pricing from './components/Pricing'
import Reviews from './components/Reviews'
import Projects from './components/Projects'
import Partner from './components/Partner'
import Footer from './components/Footer'
import Copyright from './components/Copyright'

export default function App() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* 1. Exactly Recreated Hero Section */}
      <HeroVex />

      {/* 2. Subsequent Sections */}
      <div id="explore" className="bg-white text-slate-900">
        <Marquee />
        <Testimonial />
        <Pricing />
        <Reviews />
        <Projects />
        <Partner />
        <Footer />
        <Copyright />
      </div>
    </div>
  )
}

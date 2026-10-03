import AnimatedHeading from './AnimatedHeading'
import FadeIn from './FadeIn'

export default function HeroVex() {
  const videoUrl =
    'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260403_050628_c4e32401-fab4-4a27-b7a8-6e9291cd5959.mp4'

  return (
    <section className="relative w-full h-screen overflow-hidden flex flex-col bg-black text-white">
      {/* 1. Full-screen Background Video (Raw, absolutely no dark/gradient overlay) */}
      <video
        src={videoUrl}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover z-0"
      />

      {/* 2. Hero Content (Bottom of viewport, Navbar removed) */}

      {/* 3. Hero Content (Bottom of viewport) */}
      <div className="relative z-10 w-full px-6 md:px-12 lg:px-16 flex-1 flex flex-col justify-end pb-12 lg:pb-16">
        <div className="lg:grid lg:grid-cols-2 lg:items-end gap-8">
          {/* Left Column: Heading + Subheading + Buttons */}
          <div className="flex flex-col">
            <AnimatedHeading text={'Shaping tomorrow\nwith vision and action.'} />

            <FadeIn delay={800} duration={1000}>
              <p className="text-base md:text-lg text-gray-300 mb-5 max-w-xl">
                We back visionaries and craft ventures that define what comes next.
              </p>
            </FadeIn>

            <FadeIn delay={1200} duration={1000}>
              <div className="flex flex-wrap gap-4">
                <a
                  href="#chat"
                  className="bg-white text-black px-8 py-3 rounded-lg font-medium hover:bg-gray-100 transition-colors text-center"
                >
                  Start a Chat
                </a>
                <a
                  href="#explore"
                  className="liquid-glass border border-white/20 text-white px-8 py-3 rounded-lg font-medium hover:bg-white hover:text-black transition-colors text-center"
                >
                  Explore Now
                </a>
              </div>
            </FadeIn>
          </div>

          {/* Right Column: Tag Card aligned to bottom-right */}
          <div className="flex items-end justify-start lg:justify-end mt-8 lg:mt-0">
            <FadeIn delay={1400} duration={1000}>
              <div className="liquid-glass border border-white/20 px-6 py-3 rounded-xl select-none">
                <span className="text-lg md:text-xl lg:text-2xl font-light text-white">
                  Investing. Building. Advisory.
                </span>
              </div>
            </FadeIn>
          </div>
        </div>
      </div>
    </section>
  )
}

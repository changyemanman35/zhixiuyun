import { useState, useEffect } from 'react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`sticky top-0 z-40 w-full transition-all duration-300 ${
      scrolled 
        ? 'bg-white/95 backdrop-blur-md shadow-[0_2px_12px_rgba(5,26,36,0.06)] border-b border-[#E0EBF0]' 
        : 'bg-white/80 backdrop-blur-sm border-b border-transparent'
    }`}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* 左侧 Logo */}
        <a href="/portal" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-[#051A24] flex items-center justify-center text-white font-serif font-bold text-base shadow-xs group-hover:scale-105 transition-transform duration-200">
            修
          </div>
          <span className="font-serif text-xl font-semibold tracking-tight text-[#051A24]">
            家修无忧
          </span>
          <span className="hidden sm:inline-block text-[11px] font-mono font-medium px-2 py-0.5 rounded-md bg-[#F6FCFF] text-[#273C46] border border-[#E0EBF0]">
            服务大厅
          </span>
        </a>

        {/* 中间核心导航 (四大核心板块：服务大厅 · 安全合规 · 师傅招募 · AI智能助手) */}
        <nav className="hidden md:flex items-center gap-2 text-[13.5px] font-medium text-[#273C46]">
          <a 
            href="/portal" 
            className="text-[#051A24] font-semibold px-3 py-1.5 rounded-lg bg-[#F6FCFF] border border-[#E0EBF0]/70 shadow-2xs relative"
          >
            服务大厅
            <span className="absolute -bottom-2 left-3 right-3 h-[2px] bg-[#051A24] rounded-full"></span>
          </a>
          <a 
            href="/safety" 
            className="hover:text-[#051A24] hover:bg-gray-100/70 px-3 py-1.5 rounded-lg transition-all duration-150"
          >
            安全合规
          </a>
          <a 
            href="/recruit" 
            className="hover:text-[#051A24] hover:bg-gray-100/70 px-3 py-1.5 rounded-lg transition-all duration-150"
          >
            师傅招募
          </a>
          <a 
            href="/ai-assistant" 
            className="hover:text-[#051A24] hover:bg-indigo-50/60 text-[#273C46] hover:text-indigo-900 px-3 py-1.5 rounded-lg transition-all duration-150 inline-flex items-center gap-1.5 group/ai"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 shadow-[0_0_6px_rgba(79,70,229,0.8)] group-hover/ai:scale-125 transition-transform"></span>
            <span>AI智能助手</span>
          </a>
        </nav>

        {/* 右侧快捷操作区 */}
        <div className="flex items-center gap-2 sm:gap-3">
          <a 
            href="/" 
            className="text-xs md:text-[13px] font-medium text-[#273C46] hover:text-[#051A24] px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors"
            title="进入后台工单调度控制台"
          >
            运营后台
          </a>
          <a 
            href="/login" 
            className="text-xs md:text-[13px] font-medium text-[#273C46] hover:text-[#051A24] px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors"
          >
            登录
          </a>
          <a 
            href="/orders/new" 
            className="inline-flex items-center justify-center bg-[#051A24] text-white text-xs md:text-[13px] font-medium rounded-full px-4 py-2 hover:opacity-90 active:scale-95 transition-all shadow-xs"
          >
            立即报修
          </a>
        </div>
      </div>
    </header>
  )
}

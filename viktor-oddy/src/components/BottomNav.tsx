import { Phone, MessageCircle, Calendar, MapPin } from 'lucide-react'

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-white/90 backdrop-blur-md border-t border-gray-200 py-2 px-4">
      <div className="flex justify-around items-center">
        <a href="tel:4008809966" className="flex flex-col items-center gap-0.5 text-[10px] text-[#273C46]">
          <Phone className="w-5 h-5" />
          <span>电话</span>
        </a>
        <a href="/query" className="flex flex-col items-center gap-0.5 text-[10px] text-[#273C46]">
          <MessageCircle className="w-5 h-5" />
          <span>进度查询</span>
        </a>
        <a href="/orders/new" className="flex flex-col items-center gap-0.5 text-[10px] text-[#273C46]">
          <Calendar className="w-5 h-5" />
          <span>立即预约</span>
        </a>
        <a href="/stations" className="flex flex-col items-center gap-0.5 text-[10px] text-[#273C46]">
          <MapPin className="w-5 h-5" />
          <span>服务网点</span>
        </a>
      </div>
    </nav>
  )
}

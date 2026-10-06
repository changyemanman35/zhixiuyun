export default function Copyright() {
  return (
    <div className="bg-[#051A24] border-t border-[#273C46] py-4 px-6">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row justify-between items-center text-xs text-[#6B8A99] gap-2">
        <p>© 2024 智修云 (SmartFix Cloud) 版权所有</p>
        <div className="flex gap-4">
          <a href="/" className="hover:text-white transition-colors font-medium">进入运营后台 &rarr;</a>
          <a href="/safety" className="hover:text-white transition-colors">安全合规</a>
          <a href="/recruit" className="hover:text-white transition-colors">师傅加盟</a>
          <a href="#" className="hover:text-white transition-colors">京ICP备20261001号</a>
        </div>
      </div>
    </div>
  )
}

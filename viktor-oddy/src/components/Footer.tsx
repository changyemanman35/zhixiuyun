export default function Footer() {
  return (
    <div className="bg-[#051A24] text-[#E0EBF0] py-16 px-6">
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-12">
        {/* 列1：品牌 */}
        <div>
          <h2 className="font-serif text-2xl text-white mb-4">家修无忧</h2>
          <p className="text-sm">专业家电维修服务</p>
          <p className="text-sm mt-1">让生活更省心</p>
        </div>

        {/* 列2：服务项目 */}
        <div>
          <h3 className="text-white font-medium mb-4">服务项目</h3>
          <ul className="space-y-2 text-sm">
            <li>空调维修</li>
            <li>冰箱维修</li>
            <li>洗衣机维修</li>
            <li>热水器维修</li>
            <li>油烟机维修</li>
            <li>小家电维修</li>
          </ul>
        </div>

        {/* 列3：联系方式 */}
        <div>
          <h3 className="text-white font-medium mb-4">联系我们</h3>
          <ul className="space-y-2 text-sm">
            <li>📞 400-888-9999</li>
            <li>📍 全城上门服务</li>
            <li>🕐 7×24小时在线</li>
            <li>✉️ service@jiaxiu.com</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

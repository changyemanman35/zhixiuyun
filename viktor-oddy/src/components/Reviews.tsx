import { useState, useEffect } from 'react'
import { useScrollAnimation } from '../hooks/useScrollAnimation'

const reviews = [
  { text: '海尔双开门冰箱冷冻室结冰严重，张师傅 20 分钟就赶到了，排查精准，收费比线下小广告透明太多了！', author: '王女士', location: '朝阳区天通苑' },
  { text: '滚筒洗衣机脱水剧烈晃动，平台推荐的李师傅带专用避震胶垫上门，半小时完美搞定，非常专业！', author: '赵先生', location: '海淀区知春路' },
  { text: '格力空调大热天吹热风，AI 助手一句话就帮我约好了附近师傅，线上付完 ¥30 现场核销，特别安心！', author: '孙女士', location: '西城区金融街' },
  { text: '老板油烟机电机嗡嗡响不吸烟，师傅拆机清洗换电容一气呵成，价格公道透明，值得信赖的老师傅！', author: '钱先生', location: '丰台区科技园' },
]

export default function Reviews() {
  const [currentIndex, setCurrentIndex] = useState(0)
  const { ref, isVisible } = useScrollAnimation(0.1)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % reviews.length)
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  return (
    <section id="reviews" ref={ref} className={`py-12 px-6 max-w-2xl mx-auto text-center transition-all duration-700 ease-out ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
      <div className="relative h-[160px] md:h-[200px] flex flex-col justify-center items-center">
        {reviews.map((review, index) => (
          <div
            key={index}
            className={`absolute top-0 left-0 w-full h-full flex flex-col justify-center items-center transition-opacity duration-1000 ${
              index === currentIndex ? 'opacity-100 z-10' : 'opacity-0 z-0'
            }`}
          >
            <p className="text-lg md:text-xl text-[#0D212C] leading-relaxed">
              "{review.text}"
            </p>
            <p className="text-sm text-[#273C46] mt-4 italic">
              — {review.author}, {review.location}
            </p>
          </div>
        ))}
      </div>
      <div className="flex justify-center gap-3 mt-2">
        {reviews.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentIndex(index)}
            className={`w-2.5 h-2.5 rounded-full transition-colors ${
              index === currentIndex ? 'bg-[#051A24]' : 'bg-gray-300'
            }`}
            aria-label={`Go to slide ${index + 1}`}
          />
        ))}
      </div>
    </section>
  )
}

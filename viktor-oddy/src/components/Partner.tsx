import { useScrollAnimation } from '../hooks/useScrollAnimation'

const brands = ['格力', '美的', '海尔', '西门子', '方太', '老板', '松下', '博世']

export default function Partner() {
  const { ref, isVisible } = useScrollAnimation(0.1)

  return (
    <section id="partners" ref={ref} className={`py-12 px-6 max-w-2xl mx-auto text-center transition-all duration-700 ease-out ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
      <h2 className="font-serif text-[32px] md:text-[40px] text-[#0D212C] tracking-tight mb-8">
        授权服务品牌
      </h2>
      <div className="flex flex-wrap justify-center gap-x-12 gap-y-6">
        {brands.map((brand, index) => (
          <span
            key={index}
            className="text-2xl font-medium text-slate-400 hover:text-slate-900 transition-colors duration-300 cursor-default"
          >
            {brand}
          </span>
        ))}
      </div>
      <p className="text-sm text-[#273C46] mt-8">
        官方授权维修服务商，原厂配件品质保证
      </p>
    </section>
  )
}

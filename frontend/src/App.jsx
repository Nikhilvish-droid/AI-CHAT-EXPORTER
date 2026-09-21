import Nav from './components/Nav'
import CaveHero from './components/CaveHero'
import BrandMarquee from './components/BrandMarquee'
import ProblemSolution from './components/ProblemSolution'
import HowItWorks from './components/HowItWorks/HowItWorks'
import SupportedAgents from './components/SupportedAgents'
import FAQ from './components/FAQ'
import Footer from './components/Footer'
import './App.css'

// ContentSection (old placeholder gallery) is unused — replaced by the
// real sections being built one at a time. Re-add if it's ever needed.

function App() {
  return (
    <>
      <Nav />
      <main>
        <CaveHero />
        <BrandMarquee />
        <ProblemSolution />
        <HowItWorks />
        <SupportedAgents />
        <FAQ />
      </main>
      <Footer />
    </>
  )
}

export default App

import Step1Visual from './Step1Visual'
import Step2Visual from './Step2Visual'
import Step3Visual from './Step3Visual'
import Step4Visual from './Step4Visual'

export const STEPS = [
  {
    num: '01',
    title: 'Submit Your Chat link',
    desc: 'Paste the public share link of your previous AI conversation.',
    Visual: Step1Visual,
  },
  {
    num: '02',
    title: 'Extract & Understand',
    desc: 'We fetch the conversation and run it through chunking, embeddings, retrieval and an LLM to keep only the context that matters.',
    Visual: Step2Visual,
  },
  {
    num: '03',
    title: 'Get Your Memory PDF',
    desc: 'The processed conversation becomes a structured PDF holding the context your next agent needs.',
    Visual: Step3Visual,
  },
  {
    num: '04',
    title: 'Continue With a New Agent',
    desc: 'Hand the PDF to a new chat and let it pick up exactly where the last agent stopped.',
    Visual: Step4Visual,
  },
]

export const TOTAL = String(STEPS.length).padStart(2, '0')

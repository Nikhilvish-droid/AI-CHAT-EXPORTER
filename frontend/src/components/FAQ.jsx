import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

const FAQ_ITEMS = [
  {
    question: 'Is my conversation data safe?',
    answer:
      "Your conversation is processed to extract the context needed to create your memory PDF. The system only uses the information required for the export process. Check your deployment's privacy and retention settings for the exact handling of submitted conversation data.",
  },
  {
    question: 'Do you store my conversation or chat link?',
    answer:
      'The chat link is used to access the conversation and generate the memory export. Whether conversation content, links, or generated PDFs are retained depends on the storage and retention configuration of the deployed application.',
  },
  {
    question: 'What happens after I submit my chat link?',
    answer:
      'We fetch the conversation, extract the useful content, split it into meaningful chunks, retrieve the most relevant information, and use an LLM to organize it into a structured memory PDF. The goal is to preserve what matters instead of simply copying the entire transcript.',
  },
  {
    question: 'Does the PDF contain my entire conversation?',
    answer:
      'No. The goal is not to create a transcript dump. The PDF keeps the important context, decisions, problems, solutions, technical details, code, and relevant images so another AI agent can understand where the previous conversation left off.',
  },
  {
    question: 'What information is included in the PDF?',
    answer:
      'The memory PDF is organized into four main sections: Overview, Key Decisions, Problems & Solutions, and Technical Decisions. It can also include important code, conversation images, and a list of documents that were referenced but could not be included.',
  },
  {
    question: 'Can a new AI agent continue my previous work?',
    answer:
      'Yes. Upload the generated memory PDF to your new AI conversation. It gives the new agent structured context about the previous work, including decisions, constraints, solutions, and technical details, so you can continue without explaining everything again.',
  },
  {
    question: 'What happens if a document is missing?',
    answer:
      'If the previous conversation refers to a document that could not be included in the export, the PDF can identify it in a missing documents section. The new agent can then ask you to provide the missing file or information before continuing.',
  },
  {
    question: 'Can I use the PDF with another AI platform?',
    answer:
      'Yes. The PDF is designed to be human-readable and AI-readable, so you can upload it to another AI conversation that supports file uploads and use it as context for continuing your work.',
  },
]

const EASE_OUT = [0.16, 1, 0.3, 1]

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
}

const fadeUpVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState(null)
  const prefersReducedMotion = useReducedMotion()

  const toggle = (index) => {
    setOpenIndex((current) => (current === index ? null : index))
  }

  const revealInitial = prefersReducedMotion ? 'visible' : 'hidden'

  return (
    <section className="faq-section" aria-labelledby="faq-heading">
      <motion.div
        className="faq-inner"
        variants={containerVariants}
        initial={revealInitial}
        whileInView="visible"
        viewport={{ once: true, amount: 0.2 }}
      >
        <motion.header className="faq-head" variants={fadeUpVariants}>
          <h2 id="faq-heading" className="faq-title">
            Frequently Asked Questions
          </h2>
          <p className="faq-subtitle">
            Everything you need to know about turning your old AI conversations into reusable
            memory.
          </p>
        </motion.header>

        <ul className="faq-list">
          {FAQ_ITEMS.map((item, index) => {
            const isOpen = openIndex === index
            const panelId = `faq-panel-${index}`
            const buttonId = `faq-button-${index}`

            return (
              <motion.li
                className={`faq-item${isOpen ? ' is-open' : ''}`}
                key={item.question}
                variants={fadeUpVariants}
              >
                <h3 className="faq-item-heading">
                  <button
                    type="button"
                    id={buttonId}
                    className={`faq-question${isOpen ? ' is-open' : ''}`}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => toggle(index)}
                  >
                    <span className="faq-question-text">{item.question}</span>
                    <span className={`faq-icon${isOpen ? ' is-open' : ''}`} aria-hidden="true" />
                  </button>
                </h3>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={panelId}
                      role="region"
                      aria-labelledby={buttonId}
                      className="faq-panel"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={
                        prefersReducedMotion
                          ? { duration: 0 }
                          : { duration: 0.4, ease: EASE_OUT }
                      }
                    >
                      <div className="faq-panel-inner">
                        <p className="faq-answer">{item.answer}</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.li>
            )
          })}
        </ul>
      </motion.div>
    </section>
  )
}

import { createContext, useContext } from 'react'

/** True inside a pop-up form, so the form can drop its page title (the pop-up already shows one). */
export const InModalContext = createContext(false)
export const useInModal = () => useContext(InModalContext)

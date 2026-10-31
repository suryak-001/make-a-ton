import { useLocation } from 'react-router'

/** Remembers the record that was just saved, so its row can glow briefly on the list page (instead of a toast). */
let flashed: string | undefined
let timer: number | undefined

export function setFlash(id: string | number) {
  flashed = String(id)
  window.clearTimeout(timer)
  timer = window.setTimeout(() => { flashed = undefined }, 2000) // the CSS glow fades on its own
}

/** The id to glow after landing back on a list following a save. */
export function useFlashId() {
  useLocation() // re-read when the user comes back to the list
  return flashed
}

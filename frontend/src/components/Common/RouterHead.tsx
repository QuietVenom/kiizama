import { HeadContent } from "@tanstack/react-router"
import { createPortal } from "react-dom"

const RouterHead = () => {
  if (typeof document === "undefined") {
    return null
  }

  return createPortal(<HeadContent />, document.head)
}

export default RouterHead

import { useOverlaySize } from "@/components/Responsive/useOverlaySize"
import { overlayBounds } from "@/components/Responsive/layout"
import { Dialog as ChakraDialog, Portal } from "@chakra-ui/react"
import * as React from "react"
import { CloseButton } from "./close-button"

interface DialogContentProps extends ChakraDialog.ContentProps {
  portalled?: boolean
  portalRef?: React.RefObject<HTMLElement>
  backdrop?: boolean
}

export const DialogContent = React.forwardRef<
  HTMLDivElement,
  DialogContentProps
>(function DialogContent(props, ref) {
  const {
    children,
    portalled = true,
    portalRef,
    backdrop = true,
    css,
    ...rest
  } = props

  const limitSize = useOverlaySize()
  return (
    <Portal disabled={!portalled} container={portalRef}>
      {backdrop && <ChakraDialog.Backdrop zIndex="overlay" />}
      <ChakraDialog.Positioner zIndex="modal">
        <ChakraDialog.Content
          ref={ref}
          {...rest}
          asChild={false}
          css={{
            ...css,
            "&": {
              minWidth: 0,
              overflowWrap: "anywhere",
              width: limitSize(
                rest.w ?? rest.width ?? "100%",
                overlayBounds.maxWidth,
              ),
              maxHeight: limitSize(
                rest.maxH ?? rest.maxHeight ?? "100dvh",
                overlayBounds.maxHeight,
              ),
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            },
            "& > form": {
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
              overflow: "hidden",
            },
          }}
        >
          {children}
        </ChakraDialog.Content>
      </ChakraDialog.Positioner>
    </Portal>
  )
})

export const DialogCloseTrigger = React.forwardRef<
  HTMLButtonElement,
  ChakraDialog.CloseTriggerProps
>(function DialogCloseTrigger(props, ref) {
  return (
    <ChakraDialog.CloseTrigger
      position="absolute"
      top="2"
      insetEnd="2"
      {...props}
      asChild
    >
      <CloseButton size="sm" ref={ref}>
        {props.children}
      </CloseButton>
    </ChakraDialog.CloseTrigger>
  )
})

export const DialogRoot = ChakraDialog.Root
export const DialogFooter = React.forwardRef<
  HTMLDivElement,
  ChakraDialog.FooterProps
>(function DialogFooter(props, ref) {
  return (
    <ChakraDialog.Footer ref={ref} flexWrap="wrap" flexShrink={0} {...props} />
  )
})
export const DialogHeader = React.forwardRef<
  HTMLDivElement,
  ChakraDialog.HeaderProps
>(function DialogHeader(props, ref) {
  return <ChakraDialog.Header ref={ref} flexShrink={0} pe={12} {...props} />
})
export const DialogBody = React.forwardRef<
  HTMLDivElement,
  ChakraDialog.BodyProps
>(function DialogBody(props, ref) {
  return (
    <ChakraDialog.Body
      ref={ref}
      minH={0}
      minW={0}
      overflowY="auto"
      {...props}
    />
  )
})
export const DialogBackdrop = ChakraDialog.Backdrop
export const DialogTitle = ChakraDialog.Title
export const DialogDescription = ChakraDialog.Description
export const DialogTrigger = ChakraDialog.Trigger
export const DialogActionTrigger = ChakraDialog.ActionTrigger

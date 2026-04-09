import HttpErrorScreen from "@/components/Common/HttpErrorScreen"

type ServerErrorProps = {
  message?: string
  onRetry?: () => void
}

const ServerError = ({ message, onRetry }: ServerErrorProps) => {
  return (
    <HttpErrorScreen
      dataTestId="server-error"
      statusCode={500}
      title="Something went wrong"
      message={
        message ||
        "An unexpected error prevented this page from loading correctly."
      }
      onPrimaryAction={onRetry}
      primaryActionLabel="Try Again"
      secondaryActionHref="/"
      secondaryActionLabel="Go Home"
    />
  )
}

export default ServerError

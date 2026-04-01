import HttpErrorScreen from "@/components/Common/HttpErrorScreen"

type ServiceUnavailableProps = {
  message?: string
  onRetry?: () => void
}

const ServiceUnavailable = ({ message, onRetry }: ServiceUnavailableProps) => {
  return (
    <HttpErrorScreen
      dataTestId="service-unavailable"
      statusCode={503}
      title="Service unavailable"
      message={
        message ||
        "This service is temporarily unavailable. Please try again in a moment."
      }
      onPrimaryAction={onRetry}
      primaryActionLabel="Try Again"
      secondaryActionHref="/"
      secondaryActionLabel="Go Home"
    />
  )
}

export default ServiceUnavailable

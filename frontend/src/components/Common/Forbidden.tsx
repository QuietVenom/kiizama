import HttpErrorScreen from "@/components/Common/HttpErrorScreen"

const Forbidden = () => {
  return (
    <HttpErrorScreen
      dataTestId="forbidden"
      statusCode={403}
      title="Access denied"
      message="You do not have permission to access this resource or page."
      primaryActionHref="/"
      primaryActionLabel="Go Home"
    />
  )
}

export default Forbidden

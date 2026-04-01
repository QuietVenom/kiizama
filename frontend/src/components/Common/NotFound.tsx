import HttpErrorScreen from "@/components/Common/HttpErrorScreen"

const NotFound = () => {
  return (
    <HttpErrorScreen
      dataTestId="not-found"
      statusCode={404}
      title="Oops!"
      message="The page you are looking for was not found."
      primaryActionHref="/"
      primaryActionLabel="Go Back"
    />
  )
}

export default NotFound

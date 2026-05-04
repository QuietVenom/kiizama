import { Container, Heading, Text } from "@chakra-ui/react"
import { useTranslation } from "react-i18next"

import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  const { t } = useTranslation("settings")
  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        {t("deleteAccount.title")}
      </Heading>
      <Text>{t("deleteAccount.description")}</Text>
      <DeleteConfirmation />
    </Container>
  )
}
export default DeleteAccount

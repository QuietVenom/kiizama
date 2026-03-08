import {
  Box,
  Link as ChakraLink,
  Heading,
  Stack,
  Table,
  Text,
} from "@chakra-ui/react"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { useEffect } from "react"
import InfoPageShell from "@/components/Common/InfoPageShell"

export const Route = createFileRoute("/cookie-notice")({
  component: CookieNoticePage,
})

function CookieNoticePage() {
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [])

  return (
    <InfoPageShell maxW="7xl" useSymbolHomeButton>
      <Box layerStyle="infoCard" p={{ base: 6, md: 10 }}>
        <Stack gap={8}>
          <Stack gap={2}>
            <Text textStyle="eyebrow">Company</Text>
            <Heading size={{ base: "2xl", md: "3xl" }} textStyle="pageTitle">
              Cookie Notice
            </Heading>
            <Text color="ui.mutedText" fontSize="sm">
              Last Updated: March 1, 2026
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Text textStyle="pageBody">
              This Cookie Notice explains how Kiizama ("Kiizama," "we," "us,"
              and "our") uses cookies, pixel tags, local storage, and other
              similar technologies (collectively referred to as "Cookies") to
              recognize you when you visit our public website at kiizama.com
              (the "Website"), and Kiizama's online software-as-a-service
              platform including any related APIs provided by Kiizama, together
              with all related mobile and desktop applications (collectively,
              the "Services").
            </Text>
            <Text textStyle="pageBody">
              It explains what these technologies are and why we use them, as
              well as your rights to control our use of them.
            </Text>
            <Text textStyle="pageBody">
              Please take a look at our{" "}
              <RouterLink to="/privacy" className="legal-link">
                Privacy Policy
              </RouterLink>{" "}
              if you'd like more information about how Kiizama collects, uses,
              and shares your personal information.
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">What are Cookies?</Heading>
            <Text textStyle="pageBody">
              Cookies are small text files that are placed on your computer or
              mobile device when you visit a website. Cookies contain
              information that can later be read by a web server in the domain
              that issued the cookie. Owners of a website can use Cookies for a
              variety of reasons that can include enabling their websites to
              work (or work more efficiently), providing personalized content,
              and creating website analytics.
            </Text>

            <Heading size="md">Session vs Persistent Cookies</Heading>
            <Stack gap={1} pl={4}>
              <Text textStyle="pageBody">
                • Session cookies, which are automatically deleted when you
                close your browser.
              </Text>
              <Text textStyle="pageBody">
                • Persistent cookies, which will usually remain on your device
                until you delete them or they expire.
              </Text>
            </Stack>

            <Heading size="md">First Party vs Third Party Cookies</Heading>
            <Stack gap={1} pl={4}>
              <Text textStyle="pageBody">
                • Cookies set by the website owner (in this case, Kiizama) are
                called first party cookies. Only Kiizama can access the first
                party cookies we set.
              </Text>
              <Text textStyle="pageBody">
                • Cookies set by parties other than the website owner are called
                third party cookies. Third party cookies enable third party
                features or functionality to be provided on or through the
                website (e.g., interactive content and social sharing). The
                parties that set these third party cookies can recognize your
                device both when it visits the website in question and also when
                it visits other websites that have partnered with them.
              </Text>
            </Stack>

            <Heading size="md">Other Similar Technologies</Heading>
            <Text textStyle="pageBody">
              In addition to cookies, we may use other similar technologies like
              web beacons (sometimes called "tracking pixels" or "clear gifs")
              or local storage.
            </Text>

            <Stack gap={1} pl={4}>
              <Text textStyle="pageBody">
                • Web beacons are tiny graphics files that contain a unique
                identifier that enable us to recognize when someone has visited
                our Services or opened an e-mail that we have sent them. This
                allows us, for example, to:
              </Text>
              <Stack gap={1} pl={4}>
                <Text textStyle="pageBody">
                  • monitor the traffic patterns of users from one page within
                  our Services to another,
                </Text>
                <Text textStyle="pageBody">
                  • deliver or communicate with cookies,
                </Text>
                <Text textStyle="pageBody">
                  • understand whether you have come to our Services from an
                  online advertisement displayed on a third-party website,
                </Text>
                <Text textStyle="pageBody">
                  • improve site performance, and
                </Text>
                <Text textStyle="pageBody">
                  • measure the success of e-mail marketing campaigns.
                </Text>
              </Stack>
              <Text textStyle="pageBody" pt={2}>
                • Local storage enables a website or application to store
                information locally on your device(s) in order to enable certain
                functionality in our Services. Local storage may be used to
                improve your experience with our Services, for example, by
                enabling features, remembering your preferences, and speeding up
                site functionality.
              </Text>
            </Stack>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Why does Kiizama use Cookies?</Heading>
            <Text textStyle="pageBody">
              We use Cookies for several reasons. Some Cookies are required for
              technical reasons that are essential for our Services to operate
              and to provide user-requested functionality. We refer to these as
              "Strictly Necessary" Cookies.
            </Text>
            <Text textStyle="pageBody">
              For details on specific Cookies, see{" "}
              <RouterLink to="/cookie-tables" className="legal-link">
                Kiizama Cookie Tables
              </RouterLink>
              .
            </Text>
            <Box overflowX="auto">
              <Table.Root size={{ base: "sm", md: "md" }} minW="980px">
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Types of Cookies</Table.ColumnHeader>
                    <Table.ColumnHeader>Description</Table.ColumnHeader>
                    <Table.ColumnHeader>Domain</Table.ColumnHeader>
                    <Table.ColumnHeader>
                      Who Serves These Cookies
                    </Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell> Strictly Necessary Cookies </Table.Cell>
                    <Table.Cell>
                      {" "}
                      Essential to provide you with services available through
                      our Website and Services. Because these Cookies are
                      strictly necessary to deliver the Website and Services to
                      you, they cannot be switched off in our systems. You can
                      set your browser to block or alert you about these
                      Cookies, but some parts of the Website or Services will
                      not work.{" "}
                    </Table.Cell>
                    <Table.Cell> https://kiizama.com/ </Table.Cell>
                    <Table.Cell> Kiizama </Table.Cell>
                  </Table.Row>
                  <Table.Row>
                    <Table.Cell> Functional Cookies </Table.Cell>
                    <Table.Cell>
                      {" "}
                      Enable enhanced functionality and personalization. They
                      may be set by us or by third party providers whose
                      services we have added to our pages. If you do not allow
                      these cookies then some or all of these services may not
                      function properly. These Cookies are not used in our
                      mobile apps.{" "}
                    </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                  </Table.Row>
                  <Table.Row>
                    <Table.Cell> Analytics Cookies </Table.Cell>
                    <Table.Cell>
                      {" "}
                      Allow us to count visits and traffic sources so we can
                      measure and improve site performance and functionality.
                      They help us know which pages are the most and least
                      popular and see how visitors move around the site. If you
                      do not allow these Cookies we will not know when you have
                      visited our site in order to monitor performance. These
                      Cookies are not used in our mobile apps.{" "}
                    </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                  </Table.Row>
                  <Table.Row>
                    <Table.Cell> Marketing Cookies </Table.Cell>
                    <Table.Cell>
                      {" "}
                      May be set through our site by our advertising partners to
                      build a profile of your interests and show you relevant
                      adverts on other sites. They do not store directly
                      personal information, but are based on uniquely
                      identifying your browser and internet device. If you do
                      not allow these cookies, you will experience less targeted
                      advertising. Kiizama may use advertising cookies to
                      attribute your creation of a Kiizama account to marketing
                      or advertising campaigns, for example, where a Kiizama
                      partner provides an affiliate link that you click on to
                      reach our Website. These Cookies are not used in our
                      mobile apps.{" "}
                    </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                    <Table.Cell> NA </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table.Root>
            </Box>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">How can you control Cookies?</Heading>
            <Text textStyle="pageBody">
              You have the right to decide whether to accept or reject Cookies.
              Kiizama provides settings for you to update your Cookie
              preferences in our Website and Services. These settings can be
              found in the footer of our Website. If you have a Kiizama account
              and are logged in to the Services, you can access your Cookie
              settings in the "Settings" menu section.
            </Text>
            <Text textStyle="pageBody">
              For non-logged-in users, you can also control the use of cookies
              at the browser level, by setting your web browser controls to
              accept or refuse cookies. If you choose to reject cookies, you may
              still use our Website and Services, though your access to some
              functionality and areas of our Website and Services may be
              restricted.
            </Text>
            <Text textStyle="pageBody">
              As the means by which you can refuse cookies through your web
              browser controls vary from browser-to-browser, you should visit
              your browser's help menu for more information.
            </Text>
            <Text textStyle="pageBody">
              Most advertising networks offer a way to opt out of targeted
              advertising. Learn more at{" "}
              <ChakraLink
                href="http://www.aboutads.info/choices/"
                target="_blank"
                rel="noopener noreferrer"
                className="legal-link"
              >
                http://www.aboutads.info/choices/
              </ChakraLink>
              .
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">
              How often will we update this Cookie Notice?
            </Heading>
            <Text textStyle="pageBody">
              We may update this Cookie Notice from time to time in order to
              reflect, for example, changes to the Cookies we use or for other
              operational, legal or regulatory reasons. Please therefore
              re-visit this Cookie Notice regularly to stay informed about our
              use of cookies and related technologies.
            </Text>
            <Text textStyle="pageBody">
              The date at the bottom of this Cookie Notice indicates when it was
              last updated.
            </Text>
          </Stack>

          <Stack as="section" gap={4}>
            <Heading size="lg">Where can you get further information?</Heading>
            <Text textStyle="pageBody">
              If you have any questions about our use of Cookies, please email
              us at{" "}
              <ChakraLink
                href="mailto:admin@kiizama.com"
                className="legal-link"
              >
                admin@kiizama.com
              </ChakraLink>
              .
            </Text>
          </Stack>
        </Stack>
      </Box>
    </InfoPageShell>
  )
}

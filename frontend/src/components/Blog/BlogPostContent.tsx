import { Box } from "@chakra-ui/react"
import parse from "html-react-parser"

type BlogPostContentProps = {
  html: string
}

const BlogPostContent = ({ html }: BlogPostContentProps) => {
  return (
    <Box
      data-testid="blog-post-content"
      color="ui.text"
      fontSize={{ base: "md", md: "lg" }}
      lineHeight="1.9"
      css={{
        "& h1, & h2, & h3, & h4": {
          color: "ui.text",
          fontFamily:
            "'Plus Jakarta Sans', 'Avenir Next', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
          fontWeight: "700",
          letterSpacing: "-0.02em",
          lineHeight: "1.15",
          mt: 10,
          mb: 4,
        },
        "& h1": {
          fontSize: { base: "2xl", md: "3xl" },
          mt: 0,
        },
        "& h2": {
          fontSize: { base: "xl", md: "2xl" },
        },
        "& h3": {
          fontSize: { base: "lg", md: "xl" },
        },
        "& p": {
          color: "ui.secondaryText",
          mb: 5,
        },
        "& a": {
          color: "ui.link",
          fontWeight: "600",
          textDecoration: "underline",
          textUnderlineOffset: "0.16em",
        },
        "& ul, & ol": {
          color: "ui.secondaryText",
          pl: 6,
          mb: 5,
        },
        "& li": {
          mb: 2,
        },
        "& blockquote": {
          borderLeftWidth: "4px",
          borderLeftColor: "ui.brandBorderSoft",
          bg: "ui.brandGlowSoft",
          color: "ui.text",
          px: 5,
          py: 4,
          rounded: "xl",
          mb: 6,
        },
        "& code": {
          bg: "ui.surfaceSoft",
          color: "ui.text",
          px: 1.5,
          py: 0.5,
          rounded: "md",
          fontSize: "0.9em",
        },
        "& pre": {
          bg: "ui.panelInverse",
          color: "ui.textInverse",
          p: 5,
          rounded: "2xl",
          overflowX: "auto",
          mb: 6,
        },
        "& pre code": {
          bg: "transparent",
          color: "inherit",
          p: 0,
        },
        "& table": {
          width: "100%",
          borderCollapse: "collapse",
          mb: 6,
          overflow: "hidden",
          borderRadius: "xl",
        },
        "& th, & td": {
          borderWidth: "1px",
          borderColor: "ui.borderSoft",
          px: 4,
          py: 3,
          textAlign: "left",
        },
        "& th": {
          bg: "ui.panelAlt",
          color: "ui.text",
        },
        "& img": {
          maxWidth: "100%",
          height: "auto",
          rounded: "2xl",
          my: 6,
        },
      }}
    >
      {parse(html)}
    </Box>
  )
}

export default BlogPostContent

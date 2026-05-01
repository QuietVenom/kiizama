import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { z } from "zod"
import { UsersManagementPage } from "./-components/UsersManagementPage"

const usersSearchSchema = z.object({
  page: z.number().catch(1),
})

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  validateSearch: (search) => usersSearchSchema.parse(search),
})

function Admin() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const handlePageChange = (page: number) => {
    navigate({
      to: "/admin",
      search: (prev) => ({ ...prev, page }),
    })
  }

  return <UsersManagementPage onPageChange={handlePageChange} page={page} />
}

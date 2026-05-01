import { Badge, Container, Flex, Heading, Table } from "@chakra-ui/react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { type AdminUserPublic, type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { UserActionsMenu } from "@/components/Common/UserActionsMenu"
import PendingUsers from "@/components/Pending/PendingUsers"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"
import { rethrowCriticalQueryError } from "@/features/errors/http"

const PER_PAGE = 5

const getUsersQueryOptions = ({ page }: { page: number }) => ({
  queryFn: () =>
    UsersService.readUsers({ skip: (page - 1) * PER_PAGE, limit: PER_PAGE }),
  queryKey: ["users", { page }],
})

const formatAccessLabel = (user: AdminUserPublic) => {
  if (user.managed_access_source === "admin") {
    return "Admin"
  }
  if (user.managed_access_source === "ambassador") {
    return "Ambassador"
  }
  return user.access_profile ?? "standard"
}

type UsersTableProps = {
  onPageChange: (page: number) => void
  page: number
}

function UsersTable({ onPageChange, page }: UsersTableProps) {
  const queryClient = useQueryClient()
  const currentUser = queryClient.getQueryData<UserPublic>(["currentUser"])

  const { data, error, isLoading, isPlaceholderData } = useQuery({
    ...getUsersQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
    retry: false,
  })

  rethrowCriticalQueryError(error, "query")

  const users = (data?.data.slice(0, PER_PAGE) ?? []) as AdminUserPublic[]
  const count = data?.count ?? 0

  if (isLoading) {
    return <PendingUsers />
  }

  return (
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="sm">Full name</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Email</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Role</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Access</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Plan</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Status</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {users?.map((user) => (
            <Table.Row key={user.id} opacity={isPlaceholderData ? 0.5 : 1}>
              <Table.Cell color={!user.full_name ? "gray" : "inherit"}>
                {user.full_name || "N/A"}
                {currentUser?.id === user.id && (
                  <Badge ml="1" colorPalette="design">
                    You
                  </Badge>
                )}
              </Table.Cell>
              <Table.Cell truncate maxW="sm">
                {user.email}
              </Table.Cell>
              <Table.Cell>
                {user.is_superuser ? "Superuser" : "User"}
              </Table.Cell>
              <Table.Cell textTransform="capitalize">
                {formatAccessLabel(user)}
              </Table.Cell>
              <Table.Cell textTransform="capitalize">
                {user.plan_status ?? "none"}
              </Table.Cell>
              <Table.Cell>{user.is_active ? "Active" : "Inactive"}</Table.Cell>
              <Table.Cell>
                <UserActionsMenu
                  user={user}
                  disabled={currentUser?.id === user.id}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={PER_PAGE}
          onPageChange={({ page }) => onPageChange(page)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )
}

type UsersManagementPageProps = {
  onPageChange: (page: number) => void
  page: number
}

export function UsersManagementPage({
  onPageChange,
  page,
}: UsersManagementPageProps) {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12}>
        Users Management
      </Heading>

      <AddUser />
      <UsersTable onPageChange={onPageChange} page={page} />
    </Container>
  )
}

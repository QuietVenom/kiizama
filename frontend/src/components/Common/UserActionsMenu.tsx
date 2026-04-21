import { IconButton } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { BsThreeDotsVertical } from "react-icons/bs"
import { type AdminUserPublic, UsersService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import DeleteUser from "../Admin/DeleteUser"
import EditUser from "../Admin/EditUser"
import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "../ui/menu"

interface UserActionsMenuProps {
  user: AdminUserPublic
  disabled?: boolean
}

export const UserActionsMenu = ({ user, disabled }: UserActionsMenuProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const nextAccessProfile =
    user.access_profile === "ambassador" ? "standard" : "ambassador"

  const convertMutation = useMutation({
    mutationFn: () =>
      UsersService.updateUserAccessProfile({
        userId: user.id,
        requestBody: { access_profile: nextAccessProfile },
      }),
    onSuccess: () => {
      showSuccessToast(
        nextAccessProfile === "ambassador"
          ? "User scheduled for ambassador access."
          : "User moved back to standard access.",
      )
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  return (
    <MenuRoot>
      <MenuTrigger asChild>
        <IconButton variant="ghost" color="inherit" disabled={disabled}>
          <BsThreeDotsVertical />
        </IconButton>
      </MenuTrigger>
      <MenuContent>
        {!user.is_superuser ? (
          <MenuItem
            value={`convert-${nextAccessProfile}`}
            onClick={() => convertMutation.mutate()}
            disabled={convertMutation.isPending}
            style={{ cursor: "pointer" }}
          >
            {nextAccessProfile === "ambassador"
              ? "Convert to Ambassador"
              : "Convert to Standard"}
          </MenuItem>
        ) : null}
        <EditUser user={user} />
        <DeleteUser id={user.id} />
      </MenuContent>
    </MenuRoot>
  )
}

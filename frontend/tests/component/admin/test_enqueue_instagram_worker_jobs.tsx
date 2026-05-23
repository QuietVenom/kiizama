import { QueryClient } from "@tanstack/react-query"
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test, vi } from "vitest"

import { InstagramService, type UserPublic } from "../../../src/client"
import { ApiError } from "../../../src/client/core/ApiError"
import { renderWithProviders } from "../helpers/render"

const { toast } = vi.hoisted(() => ({
  toast: {
    showErrorToast: vi.fn(),
    showSuccessToast: vi.fn(),
  },
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => toast,
}))

const EnqueueInstagramWorkerJobs = (
  await import("../../../src/components/Admin/EnqueueInstagramWorkerJobs")
).default

const createApiError = (detail: string) =>
  new ApiError(
    { method: "POST", url: "/api/v1/ig-scraper/jobs" } as never,
    {
      body: { detail },
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      url: "/api/v1/ig-scraper/jobs",
    },
    detail,
  )

const superuser: UserPublic = {
  email: "admin@example.com",
  full_name: "Admin User",
  id: "admin-user",
  is_active: true,
  is_superuser: true,
}

describe("enqueue instagram worker jobs admin tool", () => {
  beforeEach(() => {
    toast.showErrorToast.mockClear()
    toast.showSuccessToast.mockClear()
    vi.restoreAllMocks()
  })

  test("enqueue_worker_jobs_hidden_for_non_superuser", () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: Number.POSITIVE_INFINITY, retry: false },
      },
    })
    queryClient.setQueryData(["currentUser"], {
      ...superuser,
      is_superuser: false,
    } satisfies UserPublic)

    renderWithProviders(<EnqueueInstagramWorkerJobs />, { queryClient })

    expect(
      screen.queryByRole("heading", { name: "Instagram Worker Jobs" }),
    ).not.toBeInTheDocument()
  })

  test("enqueue_worker_jobs_balances_batches_and_creates_worker_jobs", async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: Number.POSITIVE_INFINITY, retry: false },
      },
    })
    queryClient.setQueryData(["currentUser"], superuser)

    const createJob = vi
      .spyOn(InstagramService, "createInstagramScrapeJob")
      .mockResolvedValueOnce({ job_id: "job-1", status: "queued" })
      .mockResolvedValueOnce({ job_id: "job-2", status: "queued" })
      .mockResolvedValueOnce({ job_id: "job-3", status: "queued" })

    renderWithProviders(<EnqueueInstagramWorkerJobs />, { queryClient })

    await user.click(
      screen.getByPlaceholderText(
        "Paste usernames, commas, spaces, or Instagram profile URLs.",
      ),
    )
    await user.paste(
      Array.from({ length: 23 }, (_, index) => `user_${index}`).join(", "),
    )
    await user.click(screen.getByRole("button", { name: "Queue Worker Jobs" }))

    await waitFor(() => {
      expect(createJob).toHaveBeenCalledTimes(3)
    })
    expect(
      createJob.mock.calls.map(([arg]) => arg.requestBody.usernames.length),
    ).toEqual([8, 8, 7])
    expect(toast.showSuccessToast).toHaveBeenCalledWith(
      "3 Instagram worker jobs created.",
    )
    expect(await screen.findByText(/Batch 1:/)).toBeVisible()
    expect(screen.getByText(/job-1/)).toBeVisible()
    expect(screen.getByText(/job-2/)).toBeVisible()
    expect(screen.getByText(/job-3/)).toBeVisible()
  })

  test("enqueue_worker_jobs_surfaces_backend_error", async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: Number.POSITIVE_INFINITY, retry: false },
      },
    })
    queryClient.setQueryData(["currentUser"], superuser)

    vi.spyOn(InstagramService, "createInstagramScrapeJob").mockRejectedValue(
      createApiError("Validation error"),
    )

    renderWithProviders(<EnqueueInstagramWorkerJobs />, { queryClient })

    await user.type(
      screen.getByPlaceholderText(
        "Paste usernames, commas, spaces, or Instagram profile URLs.",
      ),
      "therock, kikomarcos_",
    )
    await user.click(screen.getByRole("button", { name: "Queue Worker Jobs" }))

    await waitFor(() => {
      expect(toast.showErrorToast).toHaveBeenCalledWith("Validation error")
    })
  })
})

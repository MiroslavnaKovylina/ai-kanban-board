import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginPage } from "@/components/LoginPage";
import { useRouter } from "next/navigation";
import * as auth from "@/lib/auth";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

const mockedUseRouter = vi.mocked(useRouter);
const mockedLogin = vi.spyOn(auth, "login");
const mockedRegister = vi.spyOn(auth, "registerUser");

describe("LoginPage", () => {
  beforeEach(() => {
    mockedUseRouter.mockReset();
    mockedLogin.mockReset();
    mockedRegister.mockReset();
  });

  it("shows error for invalid credentials", async () => {
    mockedLogin.mockResolvedValue(false);
    render(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
  });

  it("redirects on valid credentials", async () => {
    const push = vi.fn();
    mockedUseRouter.mockReturnValue({ push } as any);
    mockedLogin.mockResolvedValue(true);

    render(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(mockedLogin).toHaveBeenCalledWith("user", "password");
    expect(push).toHaveBeenCalledWith("/");
  });

  it("creates a new account and redirects", async () => {
    const push = vi.fn();
    mockedUseRouter.mockReturnValue({ push } as any);
    mockedRegister.mockResolvedValue(true);

    render(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(mockedRegister).toHaveBeenCalledWith("newuser", "password");
    expect(push).toHaveBeenCalledWith("/");
  });
});

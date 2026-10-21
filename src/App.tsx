import { Loader2 } from "lucide-react";
import { useEffect, type ComponentType } from "react";

import { Brand } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { AuthProvider, homeForRole, nextStepFor, useAuth } from "@/lib/auth";
import { Link, matchPath, RouterProvider, usePathname, useRouter } from "@/lib/router";
import type { Role } from "@/lib/types";
import { ChangePasswordPage } from "@/pages/ChangePasswordPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { FaceEnrollmentPage } from "@/pages/FaceEnrollmentPage";
import { InstructorCallPage } from "@/pages/InstructorCallPage";
import { LeaderReservationsPage } from "@/pages/LeaderReservationsPage";
import { LoginPage } from "@/pages/LoginPage";
import { RhOutboxPage } from "@/pages/RhOutboxPage";
import { RhPeoplePage } from "@/pages/RhPeoplePage";
import { RhTrainingsPage } from "@/pages/RhTrainingsPage";
import { VerifyPage } from "@/pages/VerifyPage";

const ROLE_ROUTES: Record<string, Role> = {
  "/rh": "rh",
  "/lider": "lider",
  "/instrutor": "instrutor",
  "/funcionario": "funcionario",
};

const SUBPAGES: Record<string, { role: Role; title: string; component: ComponentType }> = {
  "/rh/pessoas": { role: "rh", title: "Pessoas", component: RhPeoplePage },
  "/rh/trainings": { role: "rh", title: "Treinamentos", component: RhTrainingsPage },
  "/rh/outbox": { role: "rh", title: "Caixa de saída", component: RhOutboxPage },
  "/lider/reservas": {
    role: "lider",
    title: "Reservas do time",
    component: LeaderReservationsPage,
  },
};

export default function App() {
  return (
    <RouterProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </RouterProvider>
  );
}

function AppRoutes() {
  const path = usePathname();
  const { user, loading } = useAuth();
  const callMatch = matchPath("/instrutor/chamadas/:id", path);
  const callMatchId = callMatch?.["id"] ?? "";

  useEffect(() => {
    const role = ROLE_ROUTES[path];
    const subpage = SUBPAGES[path];
    const verifyMatch = matchPath("/verificar/:code", path);
    if (verifyMatch?.["code"]) {
      document.title = "Verificar certificado · Trilha de Talentos";
    } else if (path === "/verificar") {
      document.title = "Verificar certificado · Trilha de Talentos";
    } else if (callMatchId) {
      document.title = "Chamada de presença · Trilha de Talentos";
    } else if (role) {
      document.title = `${role === "rh" ? "Painel do RH" : role === "lider" ? "Minha equipe" : role === "instrutor" ? "Minhas chamadas" : "Meus treinamentos"} · Trilha de Talentos`;
    } else if (subpage) {
      document.title = `${subpage.title} · Trilha de Talentos`;
    } else if (path === "/trocar-senha") {
      document.title = "Primeiro acesso · Trilha de Talentos";
    } else if (path === "/cadastro-facial") {
      document.title = "Cadastro facial · Trilha de Talentos";
    } else {
      document.title = "Entrar · Trilha de Talentos";
    }
  }, [callMatchId, path]);

  if (path === "/verificar" || matchPath("/verificar/:code", path)) {
    const params = matchPath("/verificar/:code", path);
    return <VerifyPage code={params?.["code"]} />;
  }

  if (loading) return <Splash />;

  if (path === "/") {
    if (!user) return <LoginPage />;
    return <Redirect to={nextStepFor(user)} />;
  }

  if (path === "/trocar-senha") {
    if (!user) return <Redirect to="/" />;
    if (!user.must_change_password) return <Redirect to={homeForRole(user.role)} />;
    return <ChangePasswordPage />;
  }

  if (path === "/cadastro-facial") {
    if (!user) return <Redirect to="/" />;
    if (user.must_change_password) return <Redirect to="/trocar-senha" />;
    return <FaceEnrollmentPage />;
  }

  if (callMatch) {
    if (!user) return <Redirect to="/" />;
    if (user.must_change_password) return <Redirect to="/trocar-senha" />;
    if (user.role !== "instrutor") return <Redirect to={homeForRole(user.role)} />;
    const trainingId = Number(callMatch["id"]);
    if (!Number.isInteger(trainingId) || trainingId <= 0) return <NotFoundPage loggedIn />;
    return <InstructorCallPage trainingId={trainingId} />;
  }

  const role = ROLE_ROUTES[path];
  if (role) {
    if (!user) return <Redirect to="/" />;
    if (user.must_change_password) return <Redirect to="/trocar-senha" />;
    if (user.role !== role) return <Redirect to={homeForRole(user.role)} />;
    return <DashboardPage role={role} />;
  }

  const subpage = SUBPAGES[path];
  if (subpage) {
    if (!user) return <Redirect to="/" />;
    if (user.must_change_password) return <Redirect to="/trocar-senha" />;
    if (user.role !== subpage.role) return <Redirect to={homeForRole(user.role)} />;
    const Page = subpage.component;
    return <Page />;
  }

  return <NotFoundPage loggedIn={Boolean(user)} />;
}

function Redirect({ to }: { to: string }) {
  const { navigate } = useRouter();
  useEffect(() => {
    navigate(to, { replace: true });
  }, [navigate, to]);
  return <Splash />;
}

function Splash() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background px-6">
      <Brand />
      <Loader2 className="h-5 w-5 animate-spin text-accent" />
      <p className="text-xs text-muted-foreground">Carregando...</p>
    </div>
  );
}

function NotFoundPage({ loggedIn }: { loggedIn: boolean }) {
  const { user } = useAuth();
  const home = user ? homeForRole(user.role) : "/";
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <Brand />
      <p className="text-6xl font-extrabold text-primary">404</p>
      <div>
        <h1 className="text-lg font-bold text-primary">Página não encontrada</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          O endereço acessado não existe ou foi movido. Volte para o início para continuar.
        </p>
      </div>
      <Button asChild>
        <Link to={loggedIn ? home : "/"}>{loggedIn ? "Ir para o painel" : "Voltar ao login"}</Link>
      </Button>
    </div>
  );
}

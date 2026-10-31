import { lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { RouteErrorPage } from "./pages/RouteErrorPage";

const AccountPage = lazy(() => import("./pages/AccountPage").then((page) => ({ default: page.AccountPage })));
const ForgotPasswordPage = lazy(() => import("./pages/AuthLinkPages").then((page) => ({ default: page.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("./pages/AuthLinkPages").then((page) => ({ default: page.ResetPasswordPage })));
const VerifyEmailPage = lazy(() => import("./pages/AuthLinkPages").then((page) => ({ default: page.VerifyEmailPage })));
const AirQualityPage = lazy(() => import("./pages/AirQualityPage").then((page) => ({ default: page.AirQualityPage })));
const AlertsPage = lazy(() => import("./pages/AlertsPage").then((page) => ({ default: page.AlertsPage })));
const ClimatePage = lazy(() => import("./pages/ClimatePage").then((page) => ({ default: page.ClimatePage })));
const HeatPage = lazy(() => import("./pages/HeatPage").then((page) => ({ default: page.HeatPage })));
const HomePage = lazy(() => import("./pages/HomePage").then((page) => ({ default: page.HomePage })));
const InsightsPage = lazy(() => import("./pages/InsightsPage").then((page) => ({ default: page.InsightsPage })));
const LearnPage = lazy(() => import("./pages/LearnPage").then((page) => ({ default: page.LearnPage })));
const LiveMapPage = lazy(() => import("./pages/LiveMapPage").then((page) => ({ default: page.LiveMapPage })));
const LoginPage = lazy(() => import("./pages/LoginPage").then((page) => ({ default: page.LoginPage })));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage").then((page) => ({ default: page.MethodologyPage })));
const ModelsPage = lazy(() => import("./pages/ModelsPage").then((page) => ({ default: page.ModelsPage })));
import { NotFoundPage } from "./pages/NotFoundPage";
const NotificationsPage = lazy(() => import("./pages/NotificationsPage").then((page) => ({ default: page.NotificationsPage })));
const PlaceStatusPage = lazy(() => import("./pages/PlaceStatusPage").then((page) => ({ default: page.PlaceStatusPage })));
const PlanPage = lazy(() => import("./pages/PlanPage").then((page) => ({ default: page.PlanPage })));
const QuickReportPage = lazy(() => import("./pages/QuickReportPage").then((page) => ({ default: page.QuickReportPage })));
const RainfallPage = lazy(() => import("./pages/RainfallPage").then((page) => ({ default: page.RainfallPage })));
const RegisterPage = lazy(() => import("./pages/RegisterPage").then((page) => ({ default: page.RegisterPage })));
const ReportDetailPage = lazy(() => import("./pages/ReportDetailPage").then((page) => ({ default: page.ReportDetailPage })));
const ReportFormPage = lazy(() => import("./pages/ReportFormPage").then((page) => ({ default: page.ReportFormPage })));
const ReportsPage = lazy(() => import("./pages/ReportsPage").then((page) => ({ default: page.ReportsPage })));
const RoutesPage = lazy(() => import("./pages/RoutesPage").then((page) => ({ default: page.RoutesPage })));
const SafetyPage = lazy(() => import("./pages/SafetyPage").then((page) => ({ default: page.SafetyPage })));
const SpotsPage = lazy(() => import("./pages/SpotsPage").then((page) => ({ default: page.SpotsPage })));
const WeatherPage = lazy(() => import("./pages/WeatherPage").then((page) => ({ default: page.WeatherPage })));

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "place/:areaSlug", element: <PlaceStatusPage /> },
      { path: "place/:areaSlug/:neighbourhoodSlug", element: <PlaceStatusPage /> },
      { path: "live", element: <LiveMapPage /> },
      { path: "report", element: <QuickReportPage /> },
      { path: "routes", element: <RoutesPage /> },
      { path: "plan", element: <PlanPage /> },
      { path: "safety", element: <SafetyPage /> },
      { path: "spots", element: <SpotsPage /> },
      { path: "models", element: <ModelsPage /> },
      { path: "learn", element: <LearnPage /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "weather", element: <WeatherPage /> },
      { path: "alerts", element: <AlertsPage /> },
      { path: "air-quality", element: <AirQualityPage /> },
      { path: "heat", element: <HeatPage /> },
      { path: "rainfall", element: <RainfallPage /> },
      { path: "climate", element: <ClimatePage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "reports/new", element: <ReportFormPage mode="create" /> },
      { path: "reports/:id", element: <ReportDetailPage /> },
      { path: "reports/:id/edit", element: <ReportFormPage mode="edit" /> },
      { path: "insights", element: <InsightsPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "forgot-password", element: <ForgotPasswordPage /> },
      { path: "reset-password", element: <ResetPasswordPage /> },
      { path: "verify-email", element: <VerifyEmailPage /> },
      { path: "account", element: <AccountPage /> },
      { path: "methodology", element: <MethodologyPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}

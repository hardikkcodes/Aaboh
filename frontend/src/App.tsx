import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { AccountPage } from "./pages/AccountPage";
import { AirQualityPage } from "./pages/AirQualityPage";
import { AlertsPage } from "./pages/AlertsPage";
import { ClimatePage } from "./pages/ClimatePage";
import { HeatPage } from "./pages/HeatPage";
import { HomePage } from "./pages/HomePage";
import { InsightsPage } from "./pages/InsightsPage";
import { LiveMapPage } from "./pages/LiveMapPage";
import { LoginPage } from "./pages/LoginPage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { ModelsPage } from "./pages/ModelsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PlaceStatusPage } from "./pages/PlaceStatusPage";
import { PlanPage } from "./pages/PlanPage";
import { QuickReportPage } from "./pages/QuickReportPage";
import { RainfallPage } from "./pages/RainfallPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { ReportFormPage } from "./pages/ReportFormPage";
import { ReportsPage } from "./pages/ReportsPage";
import { RoutesPage } from "./pages/RoutesPage";
import { SafetyPage } from "./pages/SafetyPage";
import { SpotsPage } from "./pages/SpotsPage";
import { WeatherPage } from "./pages/WeatherPage";

const router = createBrowserRouter([
  {
    element: <AppLayout />,
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
      { path: "account", element: <AccountPage /> },
      { path: "methodology", element: <MethodologyPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}

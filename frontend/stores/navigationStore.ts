import { create } from "zustand";
import {
  NavigationWaypoint,
  RouteCalculateRequest,
  RouteCalculateResponse,
  RouteResponse,
  GuidanceCalculationResponse,
  LiveNavigationTelemetry,
  DebrisTargetItem,
  calculateRoute,
  calculateGuidance,
  savePlannedRoute,
  listPlannedRoutes,
  getPlannedRoute,
  deletePlannedRoute,
  getLiveNavigationTelemetry,
  connectNavigationDrone,
  disconnectNavigationDrone,
  pushDroneHeartbeat,
  getDebrisNavigationTargets,
  setTelemetryStaleThreshold,
} from "../lib/api";

export type NavigationMode = "PLANNING" | "PREVIEW" | "LIVE_GUIDANCE";

export interface NavigationStoreState {
  // Drone Telemetry & Connectivity (FR-01, FR-02)
  telemetry: LiveNavigationTelemetry | null;
  isPollingTelemetry: boolean;
  staleThresholdSeconds: number;

  // Route Planning State (FR-03, FR-04, FR-05, FR-06)
  target: { latitude: number; longitude: number; name: string } | null;
  waypoints: NavigationWaypoint[];
  editingWaypointOrder: number | null;
  cruiseSpeedMps: number;
  speedSource: "USER_CONFIGURED" | "MEASURED_TELEMETRY";
  operationalLimitM: number;
  calculatedRoute: RouteCalculateResponse | null;
  guidance: GuidanceCalculationResponse | null;
  activeWaypointIndex: number;
  navigationMode: NavigationMode;
  mapClickMode: "TARGET" | "WAYPOINT" | "NONE";

  // Map & Coordinate State (FR-01)
  mapStyle: "TACTICAL" | "STREETS" | "SATELLITE";
  showAirfieldOverlay: boolean;

  // Saved Routes & Debris Targets (FR-08, FR-10)
  savedRoutes: RouteResponse[];
  debrisTargets: DebrisTargetItem[];
  isLoadingRoute: boolean;
  isSavingRoute: boolean;
  errorMessage: string | null;

  // Simulation Harness for Demonstration & Guidance Testing (FR-02, FR-11)
  simulationActive: boolean;

  // Actions
  setTarget: (target: { latitude: number; longitude: number; name: string } | null) => void;
  addWaypoint: (wp: { latitude: number; longitude: number; altitude_agl_m?: number; notes?: string }) => void;
  updateWaypoint: (order: number, partial: Partial<NavigationWaypoint>) => void;
  removeWaypoint: (order: number) => void;
  reorderWaypoint: (order: number, direction: "UP" | "DOWN") => void;
  updateWaypointAltitude: (order: number, alt: number) => void;
  setEditingWaypointOrder: (order: number | null) => void;
  clearWaypoints: () => void;
  clearAllRoute: () => void;
  setCruiseSpeed: (speed: number) => void;
  setSpeedSource: (source: "USER_CONFIGURED" | "MEASURED_TELEMETRY") => void;
  setOperationalLimit: (limitM: number) => void;
  setNavigationMode: (mode: NavigationMode) => void;
  setMapClickMode: (mode: "TARGET" | "WAYPOINT" | "NONE") => void;
  setMapStyle: (style: "TACTICAL" | "STREETS" | "SATELLITE") => void;
  toggleAirfieldOverlay: () => void;
  setActiveWaypointIndex: (idx: number) => void;
  advanceWaypoint: () => void;

  calculateRouteAction: () => Promise<RouteCalculateResponse | null>;
  saveRouteAction: (name: string) => Promise<boolean>;
  loadSavedRoutesAction: () => Promise<void>;
  loadDebrisTargetsAction: () => Promise<void>;
  loadRouteById: (id: string) => Promise<void>;
  deleteRouteAction: (id: string) => Promise<boolean>;

  fetchTelemetryOnce: () => Promise<void>;
  connectDroneAction: (droneId?: string) => Promise<boolean>;
  disconnectDroneAction: () => Promise<boolean>;
  setStaleThresholdAction: (seconds: number) => Promise<void>;
  updateGuidanceAction: () => Promise<void>;
  toggleSimulationAction: () => void;
  stepSimulationAction: () => Promise<void>;
}

export const useNavigationStore = create<NavigationStoreState>((set, get) => ({
  telemetry: null,
  isPollingTelemetry: false,
  staleThresholdSeconds: 15.0,
  target: null,
  waypoints: [],
  editingWaypointOrder: null,
  cruiseSpeedMps: 10.0,
  speedSource: "USER_CONFIGURED",
  operationalLimitM: 3000.0,
  calculatedRoute: null,
  guidance: null,
  activeWaypointIndex: 0,
  navigationMode: "PLANNING",
  mapClickMode: "TARGET",
  mapStyle: "TACTICAL",
  showAirfieldOverlay: true,
  savedRoutes: [],
  debrisTargets: [],
  isLoadingRoute: false,
  isSavingRoute: false,
  errorMessage: null,
  simulationActive: false,

  setTarget: (target) => {
    set({ target, errorMessage: null });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  addWaypoint: (wp) => {
    const current = get().waypoints;
    const newOrder = current.length + 1;
    const newWaypoint: NavigationWaypoint = {
      id: `wp_${Date.now()}_${newOrder}`,
      order: newOrder,
      latitude: Number(wp.latitude.toFixed(7)),
      longitude: Number(wp.longitude.toFixed(7)),
      altitude_agl_m: Math.max(0, wp.altitude_agl_m ?? 30.0),
      notes: wp.notes || `Waypoint #${newOrder}`,
      validation_status: "VALID",
    };
    const updated = [...current, newWaypoint];
    set({ waypoints: updated, errorMessage: null });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  updateWaypoint: (order, partial) => {
    const updated = get().waypoints.map((w) => {
      if (w.order === order) {
        return {
          ...w,
          ...partial,
          latitude: partial.latitude !== undefined ? Number(partial.latitude.toFixed(7)) : w.latitude,
          longitude: partial.longitude !== undefined ? Number(partial.longitude.toFixed(7)) : w.longitude,
          altitude_agl_m: partial.altitude_agl_m !== undefined ? Math.max(0, partial.altitude_agl_m) : w.altitude_agl_m,
        };
      }
      return w;
    });
    set({ waypoints: updated, editingWaypointOrder: null, errorMessage: null });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  setEditingWaypointOrder: (order) => set({ editingWaypointOrder: order }),

  removeWaypoint: (order) => {
    const current = get().waypoints;
    const filtered = current.filter((w) => w.order !== order);
    const reindexed = filtered.map((w, idx) => ({ ...w, order: idx + 1 }));
    set({ waypoints: reindexed, editingWaypointOrder: null });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  reorderWaypoint: (order, direction) => {
    const current = [...get().waypoints];
    const index = current.findIndex((w) => w.order === order);
    if (index === -1) return;

    const targetIndex = direction === "UP" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= current.length) return;

    const temp = current[index];
    current[index] = current[targetIndex];
    current[targetIndex] = temp;

    const updated = current.map((w, idx) => ({ ...w, order: idx + 1 }));
    set({ waypoints: updated });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  updateWaypointAltitude: (order, alt) => {
    const current = get().waypoints.map((w) =>
      w.order === order ? { ...w, altitude_agl_m: Math.max(0, alt) } : w
    );
    set({ waypoints: current });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  clearWaypoints: () => {
    set({ waypoints: [], editingWaypointOrder: null });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  clearAllRoute: () => {
    set({
      target: null,
      waypoints: [],
      editingWaypointOrder: null,
      calculatedRoute: null,
      guidance: null,
      activeWaypointIndex: 0,
      navigationMode: "PLANNING",
      errorMessage: null,
    });
  },

  setCruiseSpeed: (speed) => {
    const validSpeed = Math.max(0.5, Math.min(50, speed));
    set({ cruiseSpeedMps: validSpeed });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  setSpeedSource: (source) => {
    set({ speedSource: source });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  setOperationalLimit: (limitM) => {
    set({ operationalLimitM: Math.max(500, limitM) });
    if (get().calculatedRoute) {
      get().calculateRouteAction();
    }
  },

  setNavigationMode: (mode) => {
    if (mode === "LIVE_GUIDANCE") {
      const { telemetry, calculatedRoute } = get();
      if (!telemetry?.connected || telemetry?.is_stale || !telemetry?.has_gps_fix) {
        set({
          navigationMode: "PREVIEW",
          errorMessage:
            "Live guidance requires an active, verified drone GPS fix. Switched to Guidance Preview Mode (FR-11).",
        });
        get().updateGuidanceAction();
        return;
      }
      if (!calculatedRoute) {
        set({
          errorMessage: "Please calculate a validated flight route before engaging live guidance.",
        });
        return;
      }
    }

    set({ navigationMode: mode, errorMessage: null });
    if (mode !== "PLANNING") {
      get().updateGuidanceAction();
    }
  },

  setMapClickMode: (mode) => set({ mapClickMode: mode }),
  setMapStyle: (style) => set({ mapStyle: style }),
  toggleAirfieldOverlay: () => set((s) => ({ showAirfieldOverlay: !s.showAirfieldOverlay })),

  setActiveWaypointIndex: (idx) => {
    set({ activeWaypointIndex: idx });
    get().updateGuidanceAction();
  },

  advanceWaypoint: () => {
    const { activeWaypointIndex, waypoints } = get();
    if (activeWaypointIndex < waypoints.length) {
      set({ activeWaypointIndex: activeWaypointIndex + 1 });
      get().updateGuidanceAction();
    }
  },

  calculateRouteAction: async () => {
    const {
      target,
      waypoints,
      telemetry,
      cruiseSpeedMps,
      speedSource,
      operationalLimitM,
    } = get();

    if (!target) {
      set({ errorMessage: "Please select a target destination before calculating route." });
      return null;
    }

    // Determine start coordinates: prefer live drone GPS if connected and valid, else base threshold
    let startLat = 13.0827;
    let startLon = 80.2707;
    if (telemetry?.connected && !telemetry?.is_stale && telemetry?.latitude && telemetry?.longitude) {
      startLat = telemetry.latitude;
      startLon = telemetry.longitude;
    }

    // Determine effective speed: live telemetry vs user-configured
    let effectiveSpeed = cruiseSpeedMps;
    if (speedSource === "MEASURED_TELEMETRY" && telemetry?.speed && telemetry.speed > 0.5) {
      effectiveSpeed = telemetry.speed;
    }

    set({ isLoadingRoute: true, errorMessage: null });
    try {
      const req: RouteCalculateRequest = {
        start_latitude: startLat,
        start_longitude: startLon,
        target_latitude: target.latitude,
        target_longitude: target.longitude,
        target_name: target.name || "Target Destination",
        waypoints,
        speed_mps: effectiveSpeed,
        speed_source: speedSource,
        max_range_limit_m: operationalLimitM,
      };

      const res = await calculateRoute(req);
      set({ calculatedRoute: res, isLoadingRoute: false });
      return res;
    } catch (e: any) {
      set({ isLoadingRoute: false, errorMessage: e.message || "Route calculation failed" });
      return null;
    }
  },

  saveRouteAction: async (name: string) => {
    const { target, waypoints, telemetry, cruiseSpeedMps } = get();
    if (!target) {
      set({ errorMessage: "Cannot save route without a target destination." });
      return false;
    }
    if (!name.trim()) {
      set({ errorMessage: "Please enter a valid route name." });
      return false;
    }

    let startLat = 13.0827;
    let startLon = 80.2707;
    if (telemetry?.connected && telemetry?.latitude && telemetry?.longitude) {
      startLat = telemetry.latitude;
      startLon = telemetry.longitude;
    }

    set({ isSavingRoute: true, errorMessage: null });
    try {
      await savePlannedRoute({
        name: name.trim(),
        drone_id: telemetry?.drone_id || undefined,
        start_latitude: startLat,
        start_longitude: startLon,
        target_latitude: target.latitude,
        target_longitude: target.longitude,
        target_name: target.name,
        waypoints,
        speed_mps: cruiseSpeedMps,
        status: "PLANNED",
      });
      await get().loadSavedRoutesAction();
      set({ isSavingRoute: false });
      return true;
    } catch (e: any) {
      set({ isSavingRoute: false, errorMessage: e.message || "Failed to save route" });
      return false;
    }
  },

  loadSavedRoutesAction: async () => {
    try {
      const routes = await listPlannedRoutes(0, 50);
      set({ savedRoutes: routes });
    } catch (e: any) {
      console.error("Failed to load saved routes:", e);
    }
  },

  loadDebrisTargetsAction: async () => {
    try {
      const targets = await getDebrisNavigationTargets(40);
      set({ debrisTargets: targets });
    } catch (e: any) {
      console.error("Failed to load debris targets:", e);
    }
  },

  loadRouteById: async (id: string) => {
    set({ isLoadingRoute: true, errorMessage: null });
    try {
      const route = await getPlannedRoute(id);
      set({
        target: {
          latitude: route.target_latitude,
          longitude: route.target_longitude,
          name: route.target_name || "Target Destination",
        },
        waypoints: (route.waypoints || []).map((w, idx) => ({
          id: w.id || `wp_${route.id}_${idx + 1}`,
          order: w.order,
          latitude: w.latitude,
          longitude: w.longitude,
          altitude_agl_m: w.altitude_agl_m || 30.0,
          notes: w.notes,
          validation_status: "VALID",
        })),
        activeWaypointIndex: 0,
        navigationMode: "PLANNING",
      });
      await get().calculateRouteAction();
      set({ isLoadingRoute: false });
    } catch (e: any) {
      set({ isLoadingRoute: false, errorMessage: e.message || "Failed to load route" });
    }
  },

  deleteRouteAction: async (id: string) => {
    try {
      await deletePlannedRoute(id);
      await get().loadSavedRoutesAction();
      return true;
    } catch (e: any) {
      set({ errorMessage: e.message || "Failed to delete route" });
      return false;
    }
  },

  fetchTelemetryOnce: async () => {
    try {
      const telem = await getLiveNavigationTelemetry();
      set({
        telemetry: telem,
        staleThresholdSeconds: telem.stale_threshold_seconds || 15.0,
      });

      // Auto-revert from LIVE_GUIDANCE to PREVIEW if connection drops or goes stale
      if (get().navigationMode === "LIVE_GUIDANCE" && (!telem.connected || telem.is_stale || !telem.has_gps_fix)) {
        set({
          navigationMode: "PREVIEW",
          errorMessage: "Live telemetry lost or stale. Reverted to Guidance Preview Mode (FR-02, FR-11).",
        });
      }

      if (get().navigationMode !== "PLANNING") {
        get().updateGuidanceAction();
      }
    } catch (e: any) {
      console.warn("Failed to fetch live navigation telemetry:", e);
    }
  },

  connectDroneAction: async (droneId?: string) => {
    try {
      await connectNavigationDrone(droneId);
      await get().fetchTelemetryOnce();
      return true;
    } catch (e: any) {
      set({ errorMessage: e.message || "Failed to connect drone" });
      return false;
    }
  },

  disconnectDroneAction: async () => {
    try {
      await disconnectNavigationDrone();
      await get().fetchTelemetryOnce();
      return true;
    } catch (e: any) {
      set({ errorMessage: e.message || "Failed to disconnect drone" });
      return false;
    }
  },

  setStaleThresholdAction: async (seconds: number) => {
    try {
      await setTelemetryStaleThreshold(seconds);
      set({ staleThresholdSeconds: seconds });
      await get().fetchTelemetryOnce();
    } catch (e: any) {
      set({ errorMessage: e.message || "Failed to set stale threshold" });
    }
  },

  updateGuidanceAction: async () => {
    const { telemetry, calculatedRoute, target, waypoints, activeWaypointIndex } = get();
    if (!telemetry || !telemetry.latitude || !telemetry.longitude) return;

    let destLat: number;
    let destLon: number;
    let wpOrder: number | undefined;

    if (activeWaypointIndex < waypoints.length) {
      const activeWp = waypoints[activeWaypointIndex];
      destLat = activeWp.latitude;
      destLon = activeWp.longitude;
      wpOrder = activeWp.order;
    } else if (target) {
      destLat = target.latitude;
      destLon = target.longitude;
      wpOrder = undefined;
    } else {
      return;
    }

    try {
      const guidance = await calculateGuidance({
        drone_latitude: telemetry.latitude,
        drone_longitude: telemetry.longitude,
        drone_heading: telemetry.heading ?? undefined,
        drone_speed: telemetry.speed ?? undefined,
        target_latitude: destLat,
        target_longitude: destLon,
        waypoint_order: wpOrder,
      });

      set({ guidance });

      if (guidance.is_arrived && activeWaypointIndex < waypoints.length) {
        set({ activeWaypointIndex: activeWaypointIndex + 1 });
      }
    } catch (e) {
      console.error("Guidance update error:", e);
    }
  },

  toggleSimulationAction: () => {
    const active = !get().simulationActive;
    set({ simulationActive: active });
    if (!active && get().navigationMode === "LIVE_GUIDANCE") {
      set({ navigationMode: "PREVIEW" });
    }
  },

  stepSimulationAction: async () => {
    const { telemetry, waypoints, target, activeWaypointIndex } = get();
    if (!telemetry || !telemetry.connected) {
      await get().connectDroneAction("sim-drone-01");
    }

    const currentTelem = get().telemetry;
    const curLat = currentTelem?.latitude || 13.0827;
    const curLon = currentTelem?.longitude || 80.2707;

    let destLat = target ? target.latitude : curLat + 0.005;
    let destLon = target ? target.longitude : curLon + 0.005;

    if (activeWaypointIndex < waypoints.length) {
      destLat = waypoints[activeWaypointIndex].latitude;
      destLon = waypoints[activeWaypointIndex].longitude;
    }

    const dLat = destLat - curLat;
    const dLon = destLon - curLon;
    const dist = Math.hypot(dLat, dLon);

    let nextLat = curLat;
    let nextLon = curLon;
    let heading = currentTelem?.heading || 45.0;

    if (dist > 0.0001) {
      const step = Math.min(dist, 0.00025);
      nextLat = curLat + (dLat / dist) * step;
      nextLon = curLon + (dLon / dist) * step;
      heading = (Math.atan2(dLon, dLat) * 180) / Math.PI;
      if (heading < 0) heading += 360;
    }

    await pushDroneHeartbeat({
      drone_id: currentTelem?.drone_id || "sim-drone-01",
      telemetry_source: "SIMULATION_HARNESS",
      latitude: nextLat,
      longitude: nextLon,
      altitude: 32.5,
      speed: 10.2,
      heading: Math.round(heading),
      battery: Math.max(10, (currentTelem?.battery || 95) - 0.1),
    });

    await get().fetchTelemetryOnce();
  },
}));

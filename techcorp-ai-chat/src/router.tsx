import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen"; // généré au démarrage par le plugin Start

// TanStack Start attend un export nommé `getRouter` qui renvoie une nouvelle instance.
export function getRouter() {
  return createRouter({
    routeTree,
    defaultPreload: "intent",
    scrollRestoration: true,
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof getRouter>;
  }
}

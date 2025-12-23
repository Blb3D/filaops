/**
 * Small helper to access the ApiContext created in App.jsx
 */
import { useContext } from "react";
import { ApiContext } from "../App";

export function useApi() {
  const api = useContext(ApiContext);
  if (!api) {
    throw new Error("ApiContext not found. Wrap app with <ApiContext.Provider>.");
  }
  return api;
}


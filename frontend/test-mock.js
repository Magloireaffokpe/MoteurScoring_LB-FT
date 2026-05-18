import { api } from "./src/services/api.js";
import { setupMocks } from "./src/mocks/mockApi.js";

setupMocks();

api.post("/auth/login", { login: "admin", password: "admin1234" })
  .then(res => console.log("SUCCESS:", res.data))
  .catch(err => console.error("ERROR:", err.message));

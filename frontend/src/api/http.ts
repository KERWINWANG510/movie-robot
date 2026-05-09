import axios from "axios";

const http = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  timeout: 120_000,
});

export default http;

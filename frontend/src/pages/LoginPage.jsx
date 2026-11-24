import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { openAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    openAuth("login");
    navigate("/", { replace: true });
  }, [openAuth, navigate]);

  return null;
}

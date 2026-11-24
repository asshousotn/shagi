import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function RegisterPage() {
  const { openAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    openAuth("register");
    navigate("/", { replace: true });
  }, [openAuth, navigate]);

  return null;
}

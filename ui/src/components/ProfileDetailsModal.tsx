// src/components/ProfileDetailsModal.tsx
import React from "react";
import type { DecisionProfile } from "../types/loanModels";
import { ProfileDetails } from "./ProfileDetails";

interface Props {
  profile: DecisionProfile;
  onClose: () => void;
}

export const ProfileDetailsModal: React.FC<Props> = ({
  profile,
  onClose,
}) => {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "white",
          maxWidth: "800px",
          width: "90%",
          maxHeight: "80vh",
          overflowY: "auto",
          borderRadius: 6,
          padding: 16,
          boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h2>Profile: {profile.name}</h2>
          <button onClick={onClose}>Close</button>
        </div>
        <ProfileDetails profile={profile} />
      </div>
    </div>
  );
};

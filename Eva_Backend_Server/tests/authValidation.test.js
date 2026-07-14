const {
  validateName,
  validateUsername,
  validateEmail,
  validatePassword,
  validateRegistration,
} = require("../utils/authValidation");

describe("authValidation", () => {
  describe("validateName", () => {
    it("accepts a 2–100 char name", () => {
      expect(validateName("Al")).toBeNull();
      expect(validateName("Hamid Shehzad")).toBeNull();
    });
    it("rejects empty / too short / too long", () => {
      expect(validateName("")).toMatch(/required/i);
      expect(validateName("H")).toMatch(/at least 2/i);
      expect(validateName("a".repeat(101))).toMatch(/exceed 100/i);
    });
  });

  describe("validateUsername", () => {
    it("accepts lowercase letters, numbers, underscore (3–30)", () => {
      expect(validateUsername("hamid_815")).toBeNull();
      expect(validateUsername("abc")).toBeNull();
    });
    it("rejects uppercase, spaces, symbols, and bad length", () => {
      expect(validateUsername("Hamid")).toMatch(/lowercase/i);
      expect(validateUsername("has space")).toMatch(/lowercase/i);
      expect(validateUsername("ab")).toMatch(/3-30/);
      expect(validateUsername("a".repeat(31))).toMatch(/3-30/);
      expect(validateUsername("")).toMatch(/required/i);
    });
  });

  describe("validateEmail", () => {
    it("accepts a valid email", () => {
      expect(validateEmail("user@example.com")).toBeNull();
    });
    it("rejects malformed emails", () => {
      expect(validateEmail("nope")).toMatch(/valid email/i);
      expect(validateEmail("")).toMatch(/required/i);
    });
  });

  describe("validatePassword", () => {
    it("accepts a strong password", () => {
      expect(validatePassword("Secret123!")).toBeNull();
    });
    it("enforces length and each complexity class", () => {
      expect(validatePassword("Aa1!")).toMatch(/at least 8/i); // too short
      expect(validatePassword("ALLUPPER1!")).toMatch(/lowercase/i);
      expect(validatePassword("alllower1!")).toMatch(/uppercase/i);
      expect(validatePassword("NoNumbers!")).toMatch(/number/i);
      expect(validatePassword("NoSymbol123")).toMatch(/symbol/i);
      expect(validatePassword("")).toMatch(/required/i);
    });
  });

  describe("validateRegistration", () => {
    it("returns no errors for a fully valid payload", () => {
      const errors = validateRegistration({
        name: "Hamid",
        username: "hamid",
        email: "hamid@example.com",
        password: "Secret123!",
      });
      expect(errors).toEqual({});
    });
    it("collects one message per invalid field", () => {
      const errors = validateRegistration({
        name: "H",
        username: "Bad Name",
        email: "bad",
        password: "weak",
      });
      expect(Object.keys(errors).sort()).toEqual([
        "email",
        "name",
        "password",
        "username",
      ]);
    });
  });
});

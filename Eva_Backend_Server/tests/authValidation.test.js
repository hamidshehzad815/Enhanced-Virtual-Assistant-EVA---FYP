const {
  validateName,
  validateUsername,
  validateEmail,
  validatePassword,
  validateRegistration,
  validateLogin,
  validateResetPassword,
  throwIfErrors,
} = require("../utils/authValidation");

describe("authValidation", () => {
  describe("validateName", () => {
    it("accepts real-world names", () => {
      expect(validateName("Al")).toBeNull();
      expect(validateName("Hamid Shehzad")).toBeNull();
      expect(validateName("Mary-Jane O'Neil Jr.")).toBeNull();
      expect(validateName("José Álvarez")).toBeNull();
    });
    it("rejects empty / too short / too long / junk characters", () => {
      expect(validateName("")).toMatch(/required/i);
      expect(validateName("   ")).toMatch(/required/i);
      expect(validateName("H")).toMatch(/at least 2/i);
      expect(validateName("a".repeat(101))).toMatch(/exceed 100/i);
      expect(validateName("12345")).toMatch(/only contain letters/i);
      expect(validateName("Hamid<script>")).toMatch(/only contain letters/i);
    });
  });

  describe("validateUsername", () => {
    it("accepts letters, numbers, periods and underscores", () => {
      expect(validateUsername("hamid")).toBeNull();
      expect(validateUsername("hamid815")).toBeNull();
      expect(validateUsername("hamid_ali")).toBeNull();
      expect(validateUsername("hamid.ali")).toBeNull();
      expect(validateUsername("Hamid")).toBeNull(); // normalised to lowercase
    });
    it("rejects bad usernames with a specific reason", () => {
      expect(validateUsername("")).toMatch(/required/i);
      expect(validateUsername("ab")).toMatch(/at least 3/i);
      expect(validateUsername("a".repeat(31))).toMatch(/exceed 30/i);
      expect(validateUsername("1hamid")).toMatch(/start with a letter/i);
      expect(validateUsername("has space")).toMatch(/only contain/i);
      expect(validateUsername("ham$id")).toMatch(/only contain/i);
      expect(validateUsername("ham..id")).toMatch(/in a row/i);
      expect(validateUsername("hamid_")).toMatch(/cannot end/i);
      expect(validateUsername("admin")).toMatch(/not available/i);
    });
  });

  describe("validateEmail", () => {
    it("accepts valid emails", () => {
      expect(validateEmail("user@example.com")).toBeNull();
      expect(validateEmail("first.last+tag@sub.example.co.uk")).toBeNull();
      expect(validateEmail("f2022266297@umt.edu.pk")).toBeNull();
      expect(validateEmail("  user@example.com  ")).toBeNull();
    });
    it("rejects malformed emails", () => {
      expect(validateEmail("")).toMatch(/required/i);
      expect(validateEmail("nope")).toMatch(/valid email/i);
      expect(validateEmail("user@")).toMatch(/valid email/i);
      expect(validateEmail("user@example")).toMatch(/valid email/i);
      expect(validateEmail("user@example.c")).toMatch(/valid email/i);
      expect(validateEmail("user name@example.com")).toMatch(/valid email/i);
      expect(validateEmail("us..er@example.com")).toMatch(/valid email/i);
      expect(validateEmail(".user@example.com")).toMatch(/valid email/i);
      expect(validateEmail(`${"a".repeat(250)}@example.com`)).toMatch(/too long/i);
    });
  });

  describe("validatePassword", () => {
    it("accepts passwords produced by browser / password-manager generators", () => {
      // Chrome / Google Password Manager style: letters + digits only
      expect(validatePassword("kPq7ZmWx2NvBt9Rd")).toBeNull();
      expect(validatePassword("Xk7mPq2vRt9wLn4")).toBeNull();
      // Safari style: lowercase + digit + hyphens
      expect(validatePassword("kuzjyx-3qanzy-fopqod")).toBeNull();
      // Classic
      expect(validatePassword("Secret123!")).toBeNull();
      expect(validatePassword("secret123")).toBeNull();
      // Passphrase with symbols/spaces
      expect(validatePassword("correct horse battery staple!")).toBeNull();
    });
    it("enforces length", () => {
      expect(validatePassword("")).toMatch(/required/i);
      expect(validatePassword("Aa1!")).toMatch(/at least 8/i);
      expect(validatePassword(`A1${"b".repeat(70)}`)).toMatch(/longer than 64/i);
    });
    it("requires a letter and a number or symbol", () => {
      expect(validatePassword("12345678901")).toMatch(/letter/i);
      expect(validatePassword("onlylettershere")).toMatch(/number or symbol/i);
      expect(validatePassword("        ")).toMatch(/only spaces/i);
    });
    it("rejects common and trivial passwords", () => {
      expect(validatePassword("password123")).toMatch(/too common/i);
      expect(validatePassword("Password123")).toMatch(/too common/i);
      expect(validatePassword("qwerty123")).toMatch(/too common/i);
      expect(validatePassword("aaaaaaaa1")).not.toBeNull();
      expect(validatePassword("abcdefgh")).not.toBeNull();
    });
    it("rejects passwords containing the user's own details", () => {
      expect(
        validatePassword("hamidshehzad99", { email: "hamidshehzad@example.com" }),
      ).toMatch(/email/i);
      expect(validatePassword("MyJohnny2020", { username: "johnny" })).toMatch(
        /username/i,
      );
      // Short usernames are ignored (too many false positives)
      expect(validatePassword("Abcxyz12!", { username: "abc" })).toBeNull();
    });
  });

  describe("validateRegistration", () => {
    it("returns no errors for a fully valid payload", () => {
      expect(
        validateRegistration({
          name: "Hamid",
          username: "hamid_815",
          email: "hamid@example.com",
          password: "kPq7ZmWx2NvBt9Rd",
        }),
      ).toEqual({});
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
    it("treats non-string input as missing (no crash)", () => {
      const errors = validateRegistration({
        name: { $ne: 1 },
        username: ["a"],
        email: 42,
        password: null,
      });
      expect(Object.keys(errors).sort()).toEqual([
        "email",
        "name",
        "password",
        "username",
      ]);
    });
  });

  describe("validateLogin", () => {
    it("does not judge password strength", () => {
      expect(validateLogin({ email: "a@b.co", password: "abc" })).toEqual({});
      expect(validateLogin({ email: "a@b.co", password: "oldpass" })).toEqual({});
    });
    it("requires email and password", () => {
      const errors = validateLogin({});
      expect(errors.email).toMatch(/required/i);
      expect(errors.password).toMatch(/required/i);
      expect(validateLogin({ email: "nope", password: "x" }).email).toMatch(
        /valid email/i,
      );
    });
  });

  describe("validateResetPassword", () => {
    const base = {
      token: "abc",
      new_password: "kPq7ZmWx2NvBt9Rd",
      confirm_password: "kPq7ZmWx2NvBt9Rd",
    };
    it("accepts a generated password with matching confirmation", () => {
      expect(validateResetPassword(base)).toEqual({});
    });
    it("reports mismatch on confirm_password", () => {
      expect(
        validateResetPassword({ ...base, confirm_password: "different1" })
          .confirm_password,
      ).toMatch(/do not match/i);
    });
    it("reports weak password on new_password", () => {
      expect(
        validateResetPassword({ ...base, new_password: "short", confirm_password: "short" })
          .new_password,
      ).toMatch(/at least 8/i);
    });
    it("reports missing token", () => {
      expect(validateResetPassword({ ...base, token: "" }).token).toBeTruthy();
    });
  });

  describe("throwIfErrors", () => {
    it("uses the first specific message and exposes errors + field", () => {
      let thrown;
      try {
        throwIfErrors({ email: "Please enter a valid email address", password: "x" });
      } catch (e) {
        thrown = e;
      }
      expect(thrown.statusCode).toBe(400);
      expect(thrown.message).toBe("Please enter a valid email address");
      expect(thrown.field).toBe("email");
      expect(thrown.errors).toHaveProperty("password");
    });
    it("does nothing when there are no errors", () => {
      expect(() => throwIfErrors({})).not.toThrow();
    });
  });
});

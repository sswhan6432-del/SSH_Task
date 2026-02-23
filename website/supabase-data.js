/* ============================================
   Supabase Data — CRUD wrappers for DB tables
   Requires supabase-config.js to be loaded first
   ============================================ */

(function () {
  "use strict";

  function getClient() {
    return window.supabaseClient;
  }

  async function getUserId() {
    var client = getClient();
    if (!client) return null;
    var { data } = await client.auth.getUser();
    return data.user ? data.user.id : null;
  }

  // ─── History ───

  var history = {
    async list() {
      var client = getClient();
      if (!client) return [];
      var { data, error } = await client
        .from("history")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) { console.error("[supabaseData] history.list:", error.message); return []; }
      return data || [];
    },

    async add(entry) {
      var client = getClient();
      if (!client) return null;
      var userId = await getUserId();
      if (!userId) return null;
      var row = {
        user_id: userId,
        request: entry.request || "",
        route: entry.route || "claude",
        tasks: entry.tasks || [],
        output: entry.output || "",
      };
      var { data, error } = await client.from("history").insert(row).select().single();
      if (error) { console.error("[supabaseData] history.add:", error.message); return null; }
      return data;
    },

    async delete(id) {
      var client = getClient();
      if (!client) return false;
      var { error } = await client.from("history").delete().eq("id", id);
      if (error) { console.error("[supabaseData] history.delete:", error.message); return false; }
      return true;
    },

    async deleteAll() {
      var client = getClient();
      if (!client) return false;
      var userId = await getUserId();
      if (!userId) return false;
      var { error } = await client.from("history").delete().eq("user_id", userId);
      if (error) { console.error("[supabaseData] history.deleteAll:", error.message); return false; }
      return true;
    },
  };

  // ─── Prompts ───

  var prompts = {
    async list() {
      var client = getClient();
      if (!client) return [];
      var { data, error } = await client
        .from("prompts")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) { console.error("[supabaseData] prompts.list:", error.message); return []; }
      return data || [];
    },

    async save(prompt) {
      var client = getClient();
      if (!client) return null;
      var userId = await getUserId();
      if (!userId) return null;

      if (prompt.id) {
        // Update existing
        var { data, error } = await client
          .from("prompts")
          .update({
            name: prompt.name,
            category: prompt.category,
            template: prompt.template || prompt.content || "",
            updated_at: new Date().toISOString(),
          })
          .eq("id", prompt.id)
          .select()
          .single();
        if (error) { console.error("[supabaseData] prompts.save (update):", error.message); return null; }
        return data;
      } else {
        // Insert new
        var row = {
          user_id: userId,
          name: prompt.name,
          category: prompt.category || "other",
          template: prompt.template || prompt.content || "",
        };
        var { data, error } = await client.from("prompts").insert(row).select().single();
        if (error) { console.error("[supabaseData] prompts.save (insert):", error.message); return null; }
        return data;
      }
    },

    async delete(id) {
      var client = getClient();
      if (!client) return false;
      var { error } = await client.from("prompts").delete().eq("id", id);
      if (error) { console.error("[supabaseData] prompts.delete:", error.message); return false; }
      return true;
    },
  };

  // ─── Feedback ───

  var feedback = {
    async list() {
      var client = getClient();
      if (!client) return [];
      var { data, error } = await client
        .from("feedback")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) { console.error("[supabaseData] feedback.list:", error.message); return []; }
      return data || [];
    },

    async add(entry) {
      var client = getClient();
      if (!client) return null;
      var userId = await getUserId();
      if (!userId) return null;
      var row = {
        user_id: userId,
        session_id: entry.session_id || null,
        vote: entry.vote || null,
        comment: entry.comment || "",
      };

      // Upsert: if feedback for this session exists, update it
      if (entry.session_id) {
        var { data: existing } = await client
          .from("feedback")
          .select("id")
          .eq("user_id", userId)
          .eq("session_id", entry.session_id)
          .maybeSingle();

        if (existing) {
          var { data, error } = await client
            .from("feedback")
            .update({ vote: row.vote, comment: row.comment })
            .eq("id", existing.id)
            .select()
            .single();
          if (error) { console.error("[supabaseData] feedback.add (update):", error.message); return null; }
          return data;
        }
      }

      var { data, error } = await client.from("feedback").insert(row).select().single();
      if (error) { console.error("[supabaseData] feedback.add:", error.message); return null; }
      return data;
    },

    async delete(id) {
      var client = getClient();
      if (!client) return false;
      var { error } = await client.from("feedback").delete().eq("id", id);
      if (error) { console.error("[supabaseData] feedback.delete:", error.message); return false; }
      return true;
    },
  };

  window.supabaseData = {
    history: history,
    prompts: prompts,
    feedback: feedback,
  };
})();

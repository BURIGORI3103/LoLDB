    // 安全なテキスト描画用HTMLエスケープ
    function escapeHtml(str) {
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    // ビルド時一元管理パッチ番号
    const DEFAULT_PATCH = __DEFAULT_PATCH_JSON__;

    // インライン内包されたマスターデータ (<script>安全エスケープ済)
    const CHAMPIONS = __CHAMPIONS_JSON__;
    const ITEMS = __ITEMS_JSON__;

    __UI_HELPERS__

    let currentRole = "ALL";
    let searchKeyword = "";
    let currentAttackFilter = "ALL";
    let currentDamageFilter = "ALL";
    const currentTraitFilters = new Set();

    const gridEl = document.getElementById("champGrid");
    const countStatusEl = document.getElementById("countStatus");
    const searchInput = document.getElementById("searchInput");
    const modalEl = document.getElementById("detailModal");
    const modalCloseBtn = document.getElementById("modalCloseBtn");
    const modalNameEl = document.getElementById("modalChampName");
    const modalTitleEl = document.getElementById("modalChampTitle");
    const modalBodyEl = document.getElementById("modalBody");

    function getRoleBadgeClass(role) {
      switch(role) {
        case "TOP": return "badge-top";
        case "JUG": return "badge-jug";
        case "MID": return "badge-mid";
        case "ADC": return "badge-adc";
        case "SUP": return "badge-sup";
        default: return "badge-default";
      }
    }

    // ひらがな・カタカナ相互変換 & 柔軟検索ユーティリティ (全検索窓で共通利用)
    function toHiragana(str) {
      if (!str) return "";
      return str.replace(/[ァ-ヶ]/g, match => {
        return String.fromCharCode(match.charCodeAt(0) - 0x60);
      });
    }

    function toKatakana(str) {
      if (!str) return "";
      return str.replace(/[ぁ-ゖ]/g, match => {
        return String.fromCharCode(match.charCodeAt(0) + 0x60);
      });
    }

    function matchSearch(text, query) {
      if (!query) return true;
      if (!text) return false;
      const t = String(text).normalize("NFKC").toLowerCase();
      const q = String(query).normalize("NFKC").toLowerCase();
      if (t.includes(q)) return true;
      const th = toHiragana(t);
      const qh = toHiragana(q);
      if (th.includes(qh)) return true;
      const tk = toKatakana(t);
      const qk = toKatakana(q);
      if (tk.includes(qk)) return true;
      return false;
    }

    function renderList() {
      gridEl.innerHTML = "";
      const query = searchKeyword.trim();
      let matched = 0;

      Object.values(CHAMPIONS).forEach(champ => {
        // 1. ロールフィルター
        if (currentRole !== "ALL") {
          if (!champ.roles || !champ.roles.includes(currentRole)) return;
        }

        // 2. AA攻撃タイプフィルター (近接 / 遠隔)
        if (currentAttackFilter !== "ALL") {
          const attType = champ.attack_type?.type || (champ.stats?.attackrange <= 250 ? "MELEE" : "RANGED");
          if (currentAttackFilter === "MELEE") {
            if (attType !== "MELEE" && attType !== "HYBRID") return;
          } else if (currentAttackFilter === "RANGED") {
            if (attType !== "RANGED" && attType !== "HYBRID") return;
          } else if (currentAttackFilter === "HYBRID" && attType !== "HYBRID") return;
        }

        // 3. ダメージ属性フィルター (AD / AP / TANK)
        if (currentDamageFilter !== "ALL") {
          const pType = champ.damage_profile?.primary_type || "AD";
          if (currentDamageFilter === "AD") {
            if (pType !== "AD" && pType !== "HYBRID") return;
          } else if (currentDamageFilter === "AP") {
            if (pType !== "AP" && pType !== "HYBRID") return;
          } else if (currentDamageFilter === "TANK") {
            if (pType !== "TANK") return;
          }
        }

        // 4. 特性フィルター (サステイン / 両型あり)
        if (currentTraitFilters.has("SUSTAIN")) {
          if (!champ.sustain_info?.has_sustain) return;
        }
        if (currentTraitFilters.has("DUAL")) {
          if (!champ.damage_profile?.has_dual_build) return;
        }

        // 5. 検索クエリ (ひらがな・カタカナ・英字部分一致対応)
        if (query) {
          const isHit = matchSearch(champ.name, query) ||
                        matchSearch(champ.id, query) ||
                        matchSearch(champ.title, query);
          if (!isHit) return;
        }

        matched++;

        const card = document.createElement("div");
        card.className = "champ-card";
        card.tabIndex = 0; card.setAttribute("role", "button");
        card.onkeydown = event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(champ.id); } };
        card.onclick = () => openDetail(champ.id);

        const rolesHtml = (champ.roles || []).map(r => 
          `<span class="mini-badge ${getRoleBadgeClass(r)}">${escapeHtml(r)}</span>`
        ).join("");

        // ダメージ属性バッジ (AD / AP / HYBRID / TANK)
        const dp = champ.damage_profile || {};
        const dmgBadgeHtml = dp.badge_text ? 
          `<span class="damage-badge ${safeBadgeClass(dp.badge_class)}">${escapeHtml(dp.badge_text)}</span>` : "";

        // AA攻撃タイプバッジ (近接 / 遠隔 / 両用)
        const att = champ.attack_type || {};
        const attRange = champ.stats?.attackrange || 175;
        let attClass = "badge-melee";
        let attIcon = "🗡️";
        let attBadge = att.badge || (attRange <= 250 ? "近接" : "遠隔");
        if (att.type === "RANGED" || (!att.type && attRange > 250)) {
          attClass = "badge-ranged";
          attIcon = "🏹";
        } else if (att.type === "HYBRID") {
          attClass = "badge-att-hybrid";
          attIcon = "🔄";
        }
        const attBadgeHtml = `<span class="attack-type-badge ${attClass}" title="${escapeHtml(att.label || `${escapeHtml(attBadge)} [射程 ${attRange}]`)}">${attIcon} ${escapeHtml(attBadge)}</span>`;

        // Data Dragon公式CDNまたはフォールバック
        const patch = champ.patch || DEFAULT_PATCH;
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/champion/${champ.id}.png`;

        card.innerHTML = `
          <div class="champ-card-img-wrap">
            <img class="champ-card-img" src="${safeImageUrl(imgUrl)}" alt="${escapeHtml(champ.name)}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="champ-card-img-placeholder" style="display:none;">${escapeHtml(champ.name.charAt(0))}</div>
            <div class="role-badge-list">${rolesHtml}</div>
            <div class="card-top-badges">
              ${dmgBadgeHtml}
              ${attBadgeHtml}
            </div>
          </div>
          <div class="champ-info">
            <div class="champ-name">${escapeHtml(champ.name)}</div>
            <div class="champ-title">${escapeHtml(champ.title || "")}</div>
          </div>
        `;
        gridEl.appendChild(card);
      });

      countStatusEl.textContent = `表示中: ${matched} 体 / 全 ${Object.keys(CHAMPIONS).length} 体`;
    }

    function openDetail(champId, activeRole = null) {
      const c = CHAMPIONS[champId];
      if (!c) return;

      const patch = c.patch || DEFAULT_PATCH;
      modalNameEl.textContent = c.name;
      modalTitleEl.textContent = `${c.id} - ${c.title || ""} (Patch ${patch})`;

      const SPELL_IMG_MAP = {
        "フラッシュ": "SummonerFlash.png",
        "イグナイト": "SummonerDot.png",
        "テレポート": "SummonerTeleport.png",
        "スマイト": "SummonerSmite.png",
        "ヒール": "SummonerHeal.png",
        "バリア": "SummonerBarrier.png",
        "イグゾースト": "SummonerExhaust.png",
        "ゴースト": "SummonerHaste.png",
        "クレンズ": "SummonerBoost.png"
      };

      // 選択中ロール（未指定時は第1ロール）
      const currentSelectedRole = activeRole || (c.roles && c.roles.length > 0 ? c.roles[0] : "TOP");
      const roleSpecificData = getRoleData(c, currentSelectedRole);
      const currentSpells = roleSpecificData.spells || c.summoner_spells || [];

      // 複数ロール切り替えサブタブ
      let roleTabsHtml = "";
      if (c.roles && c.roles.length > 1) {
        roleTabsHtml = `
          <div class="modal-role-tabs">
            ${c.roles.map(r => `
              <button class="modal-role-btn ${r === currentSelectedRole ? "active" : ""}" data-modal-role="${escapeHtml(r)}">
                <span class="mini-badge ${getRoleBadgeClass(r)}">${escapeHtml(r)}</span>
                <span>${escapeHtml(r)} レーン</span>
              </button>
            `).join("")}
          </div>
        `;
      }

      // 通常攻撃 (AA) 射程タイプ (メレー / レンジ / 両用)
      const att = c.attack_type || {};
      const attRange = c.stats?.attackrange || 175;
      let attBadgeClass = "badge-melee";
      let attIcon = "🗡️";
      let attBadge = att.badge || (attRange <= 250 ? "近接" : "遠隔");
      if (att.type === "RANGED" || (!att.type && attRange > 250)) {
        attBadgeClass = "badge-ranged";
        attIcon = "🏹";
      } else if (att.type === "HYBRID") {
        attBadgeClass = "badge-att-hybrid";
        attIcon = "🔄";
      }
      const attackTypeHeaderHtml = `
        <div class="modal-attack-type-wrap">
          <span class="modal-damage-title">🎯 通常攻撃 (AA):</span>
          <span class="attack-type-badge ${attBadgeClass}">${attIcon} ${escapeHtml(att.label || `${escapeHtml(attBadge)} [射程 ${attRange}]`)}</span>
          ${att.desc ? `<span class="modal-attack-type-desc">${escapeHtml(att.desc)}</span>` : ""}
        </div>
      `;

      // ダメージ属性 ＆ 両刀プロファイル
      const dp = c.damage_profile || {};
      let damageBadgeHtml = "";
      let dualBuildAlertHtml = "";
      if (dp.badge_text) {
        damageBadgeHtml = `
          <div class="modal-damage-header">
            <span class="modal-damage-title">⚡ 主ダメージ属性:</span>
            <span class="damage-badge ${safeBadgeClass(dp.badge_class)}">${escapeHtml(dp.badge_text)} (${escapeHtml(dp.label || "")})</span>
            <span class="modal-damage-counter">🛡️ 対面時の推奨防具: <strong>${escapeHtml(dp.counter_defense || "AR/MR")}</strong></span>
          </div>
        `;
      }
      if (dp.has_dual_build) {
        dualBuildAlertHtml = `
          <div class="dual-build-alert">
            ⚡ <strong>【AD / AP 両型ビルド対応】</strong> ${escapeHtml(dp.dual_build_desc)}
          </div>
        `;
      }

      // サステイン & スキル上げ優先度バッジ
      const sustainInfo = c.sustain_info || {};
      let sustainBadgeHtml = "";
      let sustainReasonHtml = "";
      if (sustainInfo.has_sustain) {
        let badgeLabel = "🩸 サステイン所持 (重傷推奨)";
        if (sustainInfo.type === "BOTH") {
          badgeLabel = "🩸 回復＆シールド所持";
        } else if (sustainInfo.type === "SHIELD") {
          badgeLabel = "🛡️ シールド所持";
        }
        const susReason = sustainInfo.summary || sustainInfo.reason || "固有の体力回復またはシールド能力を持ちます。";
        sustainBadgeHtml = `<span class="badge-sustain">${badgeLabel}</span>`;
        sustainReasonHtml = `<div class="sustain-reason-box">⚠️ <strong>【対面注意・維持能力】</strong> ${escapeHtml(susReason)}</div>`;
      }

      const skillOrder = roleSpecificData.skill_order || "未取得";
      const skillOrderBadgeHtml = `<span class="badge-skill-order">⚡ スキル上げ順: ${escapeHtml(skillOrder)}</span>`;

      // サモナースペル（採用率上位2セット）
      const spellSets = roleSpecificData.spell_sets || c.spell_sets || [
        { name: "第1採用セット（王道・最高採用率）", spells: currentSpells }
      ];
      const spellsHtml = `
        <div class="spells-sets-wrap">
          ${spellSets.map(ss => `
            <div class="spell-set-card">
              <div class="spell-set-title">⚡ ${escapeHtml(ss.name)}</div>
              <div class="spells-badge-list">
                ${ss.spells.map(s => {
                  const sImg = SPELL_IMG_MAP[s] || "";
                  const sUrl = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/spell/${sImg}`;
                  return `
                    <span class="spell-pill">
                      <img class="spell-img" src="${safeImageUrl(sUrl)}" alt="${escapeHtml(s)}" onerror="this.style.display='none';">
                      <span>${escapeHtml(s)}</span>
                    </span>
                  `;
                }).join("")}
              </div>
            </div>
          `).join("")}
        </div>
      `;

      // スキル取得順マトリクス表 (Lv 1〜18)
      const skillMatrix = roleSpecificData.skill_matrix || {};
      const matrixSlots = ["Q", "W", "E", "R"];
      let matrixTableRows = matrixSlots.map(slot => {
        const points = skillMatrix[slot] || [];
        let cells = "";
        for (let lv = 1; lv <= 18; lv++) {
          const isActive = points.includes(lv);
          cells += `<td class="${isActive ? "skill-point-active" : ""}">${isActive ? slot : ""}</td>`;
        }
        return `<tr><td class="sticky-col">${slot}</td>${cells}</tr>`;
      }).join("");

      const skillMatrixHtml = `
        ${roleSpecificData.guidance_sources?.skill_matrix && Object.values(skillMatrix).flat().length < 18 ? '<div class="guidance-source">取得元の掲載はLv1〜15。未取得レベルは空欄です。</div>' : ""}
        <div class="skill-matrix-container">
          <div class="skill-matrix-scroll">
            <table class="skill-matrix-table">
              <thead>
                <tr>
                  <th class="sticky-col">Lv</th>
                  ${Array.from({length: 18}, (_, i) => `<th>${i+1}</th>`).join("")}
                </tr>
              </thead>
              <tbody>
                ${matrixTableRows}
              </tbody>
            </table>
          </div>
        </div>
      `;

      // 特徴・強み・弱み (フォールバック保証付き)
      const ov = c.overview || {};
      const strengthsList = ov.strengths?.length ? ov.strengths : ["確認済みデータなし"];
      const weaknessesList = ov.weaknesses?.length ? ov.weaknesses : ["確認済みデータなし"];
      const strengthsHtml = strengthsList.map(s => `<li>${escapeHtml(s)}</li>`).join("");
      const weaknessesHtml = weaknessesList.map(w => `<li>${escapeHtml(w)}</li>`).join("");

      // 立ち回りメモ
      const gn = roleSpecificData.gameplay_notes || c.gameplay_notes || {};
      const roleNoteHtml = roleSpecificData.role_note ? `<div style="font-size:12px; margin-bottom:8px; color:#38bdf8; line-height:1.5;"><strong>【${escapeHtml(currentSelectedRole)}ロールの主務】</strong> ${escapeHtml(roleSpecificData.role_note)}</div>` : "";
      const laningNote = gn.laning || "ロール専用の確認済みデータは未取得です。";
      const tfNote = gn.teamfight || "ロール専用の確認済みデータは未取得です。";
      const tipNote = gn.key_tips || "";

      // 実戦コンボ
      const combos = roleSpecificData.combos || [];
      const combosHtml = combos.map(cb => `
        <div class="combo-card">
          <div class="combo-name">🥊 ${escapeHtml(cb.name)}</div>
          <div class="combo-recipe">${escapeHtml(cb.recipe)}</div>
          <div class="combo-desc">${escapeHtml(cb.desc)}</div>
        </div>
      `).join("");

      // 複数ビルドパターン
      const buildPatterns = roleSpecificData.build_patterns || c.build_patterns || [];
      let buildTabsHtml = "";
      let buildContentHtml = "";

      function renderBuildPatternInner(bp) {
        const core = renderItemPills(bp.core_items, patch, true);
        const starter = renderItemPills(bp.starter_items, patch);
        const boots = renderItemPills(bp.boots_items, patch);
        const situational = renderItemPills(bp.situational_items, patch);
        return `<div class="build-pat-desc">💡 ${escapeHtml(bp.desc)}</div>
          <div class="build-group"><div class="build-group-title">スタートアイテム</div><div class="item-tags">${starter || "取得データなし"}</div></div>
          ${boots ? `<div class="build-group"><div class="build-group-title">推奨靴</div><div class="item-tags">${boots}</div></div>` : c.id === "Cassiopeia" ? "<div>靴：パッシブにより購入不可</div>" : ""}
          <div class="build-group"><div class="build-group-title">推奨コアアイテム（進行順）</div><div class="item-tags">${core || "取得データなし"}</div></div>
          ${situational ? `<div class="build-group"><div class="build-group-title">状況別アイテム</div><div class="item-tags">${situational}</div></div>` : ""}`;
      }

      if (buildPatterns.length > 0) {
        buildTabsHtml = `
          <div class="build-pat-tabs">
            ${buildPatterns.map((bp, idx) => `
              <button class="build-pat-btn ${idx === 0 ? "active" : ""}" data-build-idx="${idx}">${escapeHtml(bp.name)}</button>
            `).join("")}
          </div>
        `;
        buildContentHtml = `<div id="buildPatternContent">${renderBuildPatternInner(buildPatterns[0])}</div>`;
      }

      // 相性 (勝率と戦術理由を厳格分離、安全な描画、ロール固有対面データ完全対応)
      const curMatchups = roleSpecificData.matchups || c.matchups || {};

      function renderMatchupCard(m, isFav) {
        const oppImg = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/champion/${escapeHtml(m.champion_id)}.png`;
        const oppName = escapeHtml(m.name || m.champion_id);

        // 1. 勝率バッジの抽出
        let winrateText = isFav ? "有利" : "不利";
        if (m.winrate_display) {
          winrateText = m.winrate_display;
        } else if (m.winrate) {
          winrateText = `勝率 ${m.winrate}`;
        } else if (m.reason && typeof m.reason === "string") {
          const wrMatch = m.reason.match(/(\d+(?:\.\d+)?%)/);
          if (wrMatch) {
            winrateText = `勝率 ${wrMatch[1]}`;
          }
        }

        // 出典・対面・レーン・方向が一致する文献確認済み解説だけを表示する。
        const evidence = m.reason_evidence;
        const hasConfirmedReason = evidence?.confirmation === "source_confirmed"
          && evidence.champion_id === c.id && evidence.opponent_id === m.champion_id
          && evidence.role === currentSelectedRole
          && evidence.advantage === (isFav ? "favorable" : "unfavorable")
          && evidence.source_url?.startsWith("https://");
        const reasonHtml = hasConfirmedReason ? `<div class="matchup-reason">${escapeHtml(evidence.reason)}<br><a href="${safeExternalUrl(evidence.source_url)}" target="_blank" rel="noopener noreferrer">出典</a>（参照元 Patch ${escapeHtml(evidence.source_patch || "未確認")}・現在の勝率の因果関係は未検証）</div>` : "";

        const badgeClass = isFav ? "badge-fav" : "badge-unfav";

        return `
          <div class="matchup-item">
            <div class="matchup-header">
              <div class="matchup-champ-info">
                <img class="matchup-champ-img" src="${safeImageUrl(oppImg)}" alt="${oppName}" onerror="this.style.display='none';">
                <span class="matchup-champ-name">${oppName}</span>
              </div>
              <span class="${badgeClass}">${escapeHtml(winrateText)}</span>
            </div>
            ${m.games ? `<div style="font-size:11px; color:var(--text-muted);">${Number(m.games).toLocaleString("ja-JP")}試合・Patch ${escapeHtml(m.patch || patch)}・${escapeHtml(m.role || currentSelectedRole)}${m.source_url?.startsWith("https://www.op.gg/") ? `・<a href="${safeExternalUrl(m.source_url)}" target="_blank" rel="noopener noreferrer">OP.GG</a>` : ""}</div>` : ""}
            ${reasonHtml}
          </div>
        `;
      }

      let favHtml = "";
      if (curMatchups.favorable && curMatchups.favorable.length > 0) {
        favHtml = curMatchups.favorable.map(m => renderMatchupCard(m, true)).join("");
      } else {
        favHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }

      let unfavHtml = "";
      if (curMatchups.unfavorable && curMatchups.unfavorable.length > 0) {
        unfavHtml = curMatchups.unfavorable.map(m => renderMatchupCard(m, false)).join("");
      } else {
        unfavHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }

      // ルーン
      const r = roleSpecificData.runes || c.runes || {};
      const priChoices = (r.primary?.choices || []).join(" / ");
      const secChoices = (r.secondary?.choices || []).join(" / ");
      const shards = (r.shards || []).join(" / ");

      // スキル一覧
      let skillsHtml = "";
      if (c.abilities && c.abilities.length > 0) {
        c.abilities.forEach(a => {
          const pImg = a.image ? `https://ddragon.leagueoflegends.com/cdn/${patch}/img/passive/${a.image}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${safeImageUrl(pImg)}" alt="${escapeHtml(a.name)}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">P</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${escapeHtml(a.name)}</div>
                <div class="skill-desc">${escapeHtml(a.description || "")}</div>
              </div>
            </div>
          `;
        });
      }
      if (c.spells && c.spells.length > 0) {
        c.spells.forEach(s => {
          const spImg = s.image ? `https://ddragon.leagueoflegends.com/cdn/${patch}/img/spell/${s.image}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${safeImageUrl(spImg)}" alt="${escapeHtml(s.name)}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">${escapeHtml(s.slot)}</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${escapeHtml(s.name)}</div>
                <div class="skill-meta">CD: ${escapeHtml(s.cooldown || "なし")} | コスト: ${escapeHtml(s.cost || "0")}</div>
                <div class="skill-desc">${escapeHtml(s.description || "")}</div>
              </div>
            </div>
          `;
        });
      }

      modalBodyEl.innerHTML = `
        ${roleTabsHtml}

        <!-- 通常攻撃 (AA) 射程タイプ -->
        ${attackTypeHeaderHtml}

        <!-- ダメージ属性 ＆ 防具対策ガイド -->
        ${damageBadgeHtml}
        ${dualBuildAlertHtml}

        <!-- ハイライトバッジ群 -->
        <div class="champ-highlight-badges">
          ${sustainBadgeHtml}
          ${skillOrderBadgeHtml}
        </div>
        ${sustainReasonHtml}

        <!-- チャンピオン概要 (特徴・強み・弱み) -->
        <div class="detail-section">
          <div class="detail-heading">📖 チャンピオン概要（特徴・強み・弱み）</div>
          <div class="overview-text">${escapeHtml(ov.summary || "確認済みデータなし")}</div>
          ${safeExternalUrl(ov.source_url) ? `<div class="guidance-source"><a href="${safeExternalUrl(ov.source_url)}" target="_blank" rel="noopener noreferrer">概要の出典</a>・パッチ対応未検証</div>` : ""}
          <div class="pros-cons-grid">
            <div class="pros-box">
              <div class="pros-cons-title pros-title">💪 強み (Strengths)</div>
              <ul class="pros-cons-ul">${strengthsHtml}</ul>
            </div>
            <div class="cons-box">
              <div class="pros-cons-title cons-title">⚠️ 弱み (Weaknesses)</div>
              <ul class="pros-cons-ul">${weaknessesHtml}</ul>
            </div>
          </div>
        </div>

        <!-- 立ち回りメモ & スキル吐きどころ -->
        <div class="detail-section">
          <div class="detail-heading">📝 立ち回り概要メモ & スキルの吐きどころ</div>
          ${roleNoteHtml}
          ${guidanceSourcesHtml(roleSpecificData)}
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【序盤・レーン戦】</strong> ${escapeHtml(laningNote)}</div>
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【中終盤・集団戦】</strong> ${escapeHtml(tfNote)}</div>
          ${tipNote ? `<div style="font-size:12px; color:#f59e0b; line-height:1.5;"><strong>【極意】</strong> ${escapeHtml(tipNote)}</div>` : ""}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">📚 wiki掲載の敵・味方との相性</div>
          <div style="font-size:11px; color:var(--text-muted); margin-bottom:8px;">折りたたみ内を含む掲載文の自動抽出。ロール・現在パッチの指定なし。OP.GGの勝率理由とは別の資料です。</div>
          ${(c.wiki_matchups?.groups || []).map(g => `<details style="margin-bottom:10px;"><summary>${g.relation === "ally" ? "味方" : "敵"}・${g.advantage === "favorable" ? "有利／相性良好" : "不利／相性不良"}：${escapeHtml(g.label || "対象チャンピオン")}（${g.champion_ids.map(id => escapeHtml(CHAMPIONS[id]?.name || id)).join("、")}）</summary><p style="font-size:12px; white-space:pre-wrap; line-height:1.7;">${escapeHtml(g.text)}</p></details>`).join("") || "構造化して取得できた相性項目はありません。"}
          ${c.wiki_matchups?.source_url?.startsWith("https://www.loljp-wiki.jp/") ? `<a href="${safeExternalUrl(c.wiki_matchups.source_url)}" target="_blank" rel="noopener noreferrer">出典の相性・対策欄を開く</a>` : ""}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">📖 wikiの考察・対策</div>
          ${Object.entries(c.wiki_info?.sections || {}).map(([heading, text]) => `<div style="font-size:12px; margin-bottom:8px;">${escapeHtml(heading)}：${escapeHtml(text)}</div>`).join("")}
          <div style="font-size:11px; color:var(--text-muted);">取得日：${escapeHtml((c.wiki_info?.fetched_at || "").slice(0, 10))}・パッチ対応未検証</div>
          ${c.wiki_info?.source_url?.startsWith("https://www.loljp-wiki.jp/") ? `<a href="${safeExternalUrl(c.wiki_info.source_url)}" target="_blank" rel="noopener noreferrer">出典：LoLJPWiki</a>` : ""}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">🥊 実戦コンボ・スキル回し（Flash併用含む）</div>
          <div class="combo-grid">${combosHtml || "確認済みのロール専用コンボは未取得です。"}</div>
        </div>

        <!-- 推奨スペル -->
        <div class="detail-section">
          <div class="detail-heading">⚔️ 推奨サモナースペル（${escapeHtml(currentSelectedRole)}運用・採用率上位）</div>
          ${spellsHtml}
        </div>

        <!-- 推奨ビルド (複数パターン切り替え) -->
        <div class="detail-section">
          <div class="detail-heading">🛡️ 推奨ビルド構成（複数パターン対応）</div>
          ${buildTabsHtml}
          ${buildContentHtml}
        </div>

        <!-- 対面相性 -->
        <div class="detail-section">
          <div class="detail-heading">⚖️ 対面相性（OP.GG 統計勝率）</div>
          <div class="matchups-container">
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--favorable); margin-bottom:6px;">📈 有利な対面（おすすめ）</div>
              ${favHtml}
            </div>
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--unfavorable); margin-bottom:6px;">📉 不利な対面（警戒）</div>
              ${unfavHtml}
            </div>
          </div>
        </div>

        <!-- ルーン構成 -->
        <div class="detail-section">
          <div class="detail-heading">🔮 推奨ルーン構成</div>
          <div class="rune-row"><span class="rune-title">メインパス [${escapeHtml(r.primary?.path || "未取得")}]:</span><strong>${escapeHtml(r.primary?.keystone_name || "未取得")}</strong> (${escapeHtml(priChoices)})</div>
          <div class="rune-row"><span class="rune-title">サブパス [${escapeHtml(r.secondary?.path || "未取得")}]:</span>${escapeHtml(secChoices)}</div>
          <div class="rune-row"><span class="rune-title">シャード:</span>${escapeHtml(shards)}</div>
        </div>

        <!-- 全スキル詳細 -->
        <div class="detail-section">
          <div class="detail-heading">⚡ スキル詳細 & スキル取得順マトリクス</div>
          <div style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:8px;">📊 レベル別取得テーブル (Lv 1〜18)</div>
          ${skillMatrixHtml}
          <div style="font-size:12px; font-weight:700; color:var(--text-muted); margin:16px 0 8px 0;">🎯 各スキル性能解説</div>
          ${skillsHtml}
        </div>
      `;

      // ロールサブタブのイベント登録
      modalBodyEl.querySelectorAll(".modal-role-btn").forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const targetRole = btn.getAttribute("data-modal-role");
          openDetail(champId, targetRole);
        };
      });

      // ビルドパターン切り替えタブのイベント登録
      modalBodyEl.querySelectorAll(".build-pat-btn").forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          modalBodyEl.querySelectorAll(".build-pat-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const idx = parseInt(btn.getAttribute("data-build-idx"), 10);
          const bp = buildPatterns[idx];
          const contentBox = document.getElementById("buildPatternContent");
          if (contentBox && bp) {
            contentBox.innerHTML = renderBuildPatternInner(bp);
            bindClickableItems(contentBox);
          }
        };
      });

      // アイテムクリックイベントの登録関数
      function bindClickableItems(parentEl) {
        parentEl.querySelectorAll(".clickable-item").forEach(el => {
          el.onclick = (e) => {
            e.stopPropagation();
            const itemId = el.getAttribute("data-item-id");
            if (itemId && ITEMS[itemId]) {
              openItemDetail(itemId);
            }
          };
        });
      }
      bindClickableItems(modalBodyEl);

      modalEl.classList.add("open");

      // スクロール位置を必ず一番上（最上部）にリセット
      const mContent = modalEl.querySelector(".modal-content");
      if (mContent) mContent.scrollTop = 0;
      modalBodyEl.scrollTop = 0;

      recordModal({modal: 'champion_detail', champId, role: currentSelectedRole});
    }
    modalCloseBtn.onclick = closeTopModal;
    modalEl.onclick = event => { if (event.target === modalEl) closeTopModal(); };

    // リリースノート（アプデ履歴）モーダル制御
    const changelogModalEl = document.getElementById("changelogModal");
    const changelogCloseBtn = document.getElementById("changelogCloseBtn");
    const patchBadgeEl = document.getElementById("patchBadge");

    function openChangelogModal() {
      changelogModalEl.classList.add("open");
      const cContent = changelogModalEl.querySelector(".modal-content");
      if (cContent) cContent.scrollTop = 0;
      recordModal({modal: 'changelog'});
    }
    if (patchBadgeEl) {
      patchBadgeEl.onclick = openChangelogModal;
      patchBadgeEl.tabIndex = 0; patchBadgeEl.setAttribute("role", "button");
      patchBadgeEl.onkeydown = event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openChangelogModal(); } };
    }
    changelogCloseBtn.onclick = closeTopModal;
    changelogModalEl.onclick = event => { if (event.target === changelogModalEl) closeTopModal(); };

    // ==========================================
    // アイテム詳細モーダル制御 (Phase 2)
    // ==========================================
    const itemDetailModalEl = document.getElementById("itemDetailModal");
    const itemDetailCloseBtn = document.getElementById("itemDetailCloseBtn");
    const itemDetailIcon = document.getElementById("itemDetailIcon");
    const itemDetailName = document.getElementById("itemDetailName");
    const itemDetailPrices = document.getElementById("itemDetailPrices");
    const itemDetailStatsSec = document.getElementById("itemDetailStatsSec");
    const itemDetailStatsText = document.getElementById("itemDetailStatsText");
    const itemDetailDescSec = document.getElementById("itemDetailDescSec");
    const itemDetailDescText = document.getElementById("itemDetailDescText");
    const itemDetailRecipeSec = document.getElementById("itemDetailRecipeSec");
    const itemRecipeFromBox = document.getElementById("itemRecipeFromBox");
    const itemRecipeFromList = document.getElementById("itemRecipeFromList");
    const itemRecipeIntoBox = document.getElementById("itemRecipeIntoBox");
    const itemRecipeIntoList = document.getElementById("itemRecipeIntoList");

    function openItemDetail(itemId) {
      const item = ITEMS[itemId];
      if (!item) return;

      const patch = DEFAULT_PATCH;
      itemDetailIcon.src = safeImageUrl(`https://ddragon.leagueoflegends.com/cdn/${patch}/img/item/${item.id}.png`);
      itemDetailIcon.style.display = "block";
      itemDetailName.textContent = item.display_name || item.name;

      // 価格
      const totalGold = item.gold?.total || 0;
      const sellGold = item.gold?.sell || 0;
      itemDetailPrices.innerHTML = `
        <span class="item-card-price">💰 価格: ${escapeHtml(totalGold)} G</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">(売却: ${escapeHtml(sellGold)} G)</span>
      `;

      // ステータス整形 (絵文字・アイコンなしのクリーン表示)
      const statsList = item.stats_list || [];
      if (statsList.length > 0) {
        itemDetailStatsSec.style.display = "block";
        itemDetailStatsText.innerHTML = statsList.map(st => `<span class="stat-badge">${escapeHtml(st)}</span>`).join("");
      } else {
        const statsObj = item.stats || {};
        const statEntries = Object.entries(statsObj);
        if (statEntries.length > 0) {
          itemDetailStatsSec.style.display = "block";
          const statsHtml = statEntries.map(([k, v]) => {
            let label = k;
            let val = v;
            if (k === "FlatPhysicalDamageMod") label = "攻撃力(AD)";
            else if (k === "FlatMagicDamageMod") label = "魔力(AP)";
            else if (k === "FlatHPPoolMod") label = "体力(HP)";
            else if (k === "FlatArmorMod") label = "物理防御(AR)";
            else if (k === "FlatSpellBlockMod") label = "魔法防御(MR)";
            else if (k === "PercentAttackSpeedMod") { label = "攻撃速度"; val = `+${Math.round(val * 100)}%`; }
            else if (k === "FlatMovementSpeedMod") label = "移動速度";
            else if (k === "PercentMovementSpeedMod") { label = "移動速度%"; val = `+${Math.round(val * 100)}%`; }
            else if (k === "FlatCritChanceMod") { label = "クリティカル率"; val = `+${Math.round(val * 100)}%`; }
            else if (k === "FlatMPPoolMod") label = "マナ";
            else if (k === "PercentLifeStealMod") { label = "ライフスティール"; val = `+${Math.round(val * 100)}%`; }
            else if (k === "PercentOmnivampMod") { label = "オムニヴァンプ"; val = `+${Math.round(val * 100)}%`; }
            else if (k === "PercentTenacityMod") { label = "行動妨害耐性"; val = `+${Math.round(val * 100)}%`; }

            if (typeof val === "number" && !val.toString().startsWith("+") && val > 0) {
              val = `+${escapeHtml(val)}`;
            }
            return `<span class="stat-badge">${escapeHtml(label)}: ${escapeHtml(val)}</span>`;
          }).join("");
          itemDetailStatsText.innerHTML = statsHtml;
        } else {
          itemDetailStatsSec.style.display = "none";
        }
      }

      // 説明文整形
      let cleanDesc = item.description || item.plaintext || "効果情報なし";
      cleanDesc = cleanDesc.replace(/<br\s*\/?>/gi, "\n")
                           .replace(/<\/p>/gi, "\n")
                           .replace(/<li>/gi, "• ")
                           .replace(/<\/li>/gi, "\n")
                           .replace(/<[^>]+>/g, "")
                           .trim();
      itemDetailDescText.textContent = cleanDesc;

      // 素材ツリー (Builds from)
      const fromIds = item.from || [];
      if (fromIds.length > 0) {
        itemRecipeFromBox.style.display = "block";
        itemRecipeFromList.innerHTML = fromIds.map(fid => {
          const fItem = ITEMS[fid];
          const fName = fItem ? fItem.name : `ID:${escapeHtml(fid)}`;
          const fPrice = fItem ? `${fItem.gold?.total || 0} G` : "無料";
          const fImg = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/item/${escapeHtml(fid)}.png`;
          const fStats = fItem?.stats_summary ? `<span style="font-size:10px; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(fItem.stats_summary)}</span>` : "";
          return `
            <div class="recipe-item-card" data-recipe-id="${escapeHtml(fid)}" title="${escapeHtml(fName)} の詳細を表示">
              <img src="${safeImageUrl(fImg)}" alt="${escapeHtml(fName)}" onerror="this.src='icon.png';">
              <div class="recipe-item-info">
                <span class="recipe-item-name">${escapeHtml(fName)}</span>
                <span class="recipe-item-price">💰 ${escapeHtml(fPrice)}</span>
                ${fStats}
              </div>
            </div>
          `;
        }).join("");
      } else {
        itemRecipeFromBox.style.display = "none";
      }

      // 派生先ツリー (Builds into)
      const intoIds = item.into || [];
      if (intoIds.length > 0) {
        itemRecipeIntoBox.style.display = "block";
        itemRecipeIntoList.innerHTML = intoIds.map(iid => {
          const iItem = ITEMS[iid];
          const iName = iItem ? iItem.name : `ID:${escapeHtml(iid)}`;
          const iPrice = iItem ? `${iItem.gold?.total || 0} G` : "無料";
          const iImg = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/item/${escapeHtml(iid)}.png`;
          const iStats = iItem?.stats_summary ? `<span style="font-size:10px; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(iItem.stats_summary)}</span>` : "";
          return `
            <div class="recipe-item-card" data-recipe-id="${escapeHtml(iid)}" title="${escapeHtml(iName)} の詳細を表示">
              <img src="${safeImageUrl(iImg)}" alt="${escapeHtml(iName)}" onerror="this.src='icon.png';">
              <div class="recipe-item-info">
                <span class="recipe-item-name">${escapeHtml(iName)}</span>
                <span class="recipe-item-price">💰 ${escapeHtml(iPrice)}</span>
                ${iStats}
              </div>
            </div>
          `;
        }).join("");
      } else {
        itemRecipeIntoBox.style.display = "none";
      }

      if (fromIds.length === 0 && intoIds.length === 0) {
        itemDetailRecipeSec.style.display = "none";
      } else {
        itemDetailRecipeSec.style.display = "block";
      }

      // レシピアイテムのクリックイベント（素材・派生先アイテム詳細へジャンプ）
      itemDetailModalEl.querySelectorAll(".recipe-item-card, .recipe-item-pill").forEach(pill => {
        pill.onclick = (e) => {
          e.stopPropagation();
          const nextId = pill.getAttribute("data-recipe-id");
          if (nextId) openItemDetail(nextId);
        };
      });

      itemDetailModalEl.classList.add("open");
      const iContent = itemDetailModalEl.querySelector(".modal-content");
      if (iContent) iContent.scrollTop = 0;
      const iBody = itemDetailModalEl.querySelector(".modal-body");
      if (iBody) iBody.scrollTop = 0;

      recordModal({modal: 'item_detail', itemId: String(itemId)});
    }
    itemDetailCloseBtn.onclick = closeTopModal;
    itemDetailModalEl.onclick = event => { if (event.target === itemDetailModalEl) closeTopModal(); };

    // ==========================================
    // アイテム図鑑の制御・検索・ソート (Phase 2)
    // ==========================================
    const itemsGridEl = document.getElementById("itemsGrid");
    const itemCountStatusEl = document.getElementById("itemCountStatus");
    const itemSearchInput = document.getElementById("itemSearchInput");
    const itemSortSelect = document.getElementById("itemSortSelect");
    let currentItemCat = "ALL";
    let itemSearchKeyword = "";
    let currentItemSort = "price_desc";

    function renderItemsList() {
      if (!itemsGridEl) return;
      itemsGridEl.innerHTML = "";
      const query = itemSearchKeyword.trim();

      let itemsList = Object.values(ITEMS);

      // 1. カテゴリフィルター
      if (currentItemCat !== "ALL") {
        itemsList = itemsList.filter(item => {
          if (Array.isArray(item.categories)) {
            return item.categories.includes(currentItemCat);
          }
          if (typeof item.category === "string") {
            return item.category === currentItemCat;
          }
          return false;
        });
      }

      // 2. ステータスチェックボックスフィルター (複数選択 AND条件)
      const checkedBoxes = document.querySelectorAll(".stat-filter-chk:checked");
      const selectedStats = Array.from(checkedBoxes).map(cb => cb.value);

      const activeStatBadge = document.getElementById("activeStatBadge");
      if (activeStatBadge) {
        if (selectedStats.length > 0) {
          activeStatBadge.textContent = selectedStats.length;
          activeStatBadge.style.display = "inline-flex";
        } else {
          activeStatBadge.style.display = "none";
        }
      }

      if (selectedStats.length > 0) {
        itemsList = itemsList.filter(item => {
          const itemTags = item.stat_tags || [];
          return selectedStats.every(tag => itemTags.includes(tag));
        });
      }

      // 3. 検索フィルター (ひらがな・カタカナ・通称・部分一致対応)
      if (query) {
        itemsList = itemsList.filter(item => {
          return matchSearch(item.name, query) ||
                 matchSearch(item.colloq, query) ||
                 matchSearch(item.plaintext, query) ||
                 matchSearch(item.stats_summary, query) ||
                 matchSearch(item.description, query);
        });
      }

      // 4. ソート
      itemsList.sort((a, b) => {
        if (currentItemSort === "price_desc") {
          return (b.gold?.total || 0) - (a.gold?.total || 0);
        } else if (currentItemSort === "price_asc") {
          return (a.gold?.total || 0) - (b.gold?.total || 0);
        } else if (currentItemSort === "name_asc") {
          return (a.name || "").localeCompare(b.name || "", "ja");
        }
        return 0;
      });

      itemsList.forEach(item => {
        const card = document.createElement("div");
        card.className = "item-grid-card";
        card.tabIndex = 0; card.setAttribute("role", "button");
        card.onkeydown = event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openItemDetail(item.id); } };
        card.onclick = () => openItemDetail(item.id);

        const patch = DEFAULT_PATCH;
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/item/${item.id}.png`;
        const price = item.gold?.total ? `${item.gold.total} G` : "無料";
        const statsSummary = item.stats_summary ? `<div class="item-card-stats" title="${escapeHtml(item.stats_summary)}">${escapeHtml(item.stats_summary)}</div>` : "";

        card.innerHTML = `
          <img class="item-card-icon" src="${safeImageUrl(imgUrl)}" alt="${escapeHtml(item.display_name || item.name)}" loading="lazy" onerror="this.src='icon.png';">
          <div class="item-card-name" title="${escapeHtml(item.display_name || item.name)}">${escapeHtml(item.display_name || item.name)}</div>
          <div class="item-card-price">💰 ${escapeHtml(price)}</div>
          ${statsSummary}
        `;
        itemsGridEl.appendChild(card);
      });

      if (itemCountStatusEl) {
        itemCountStatusEl.textContent = `表示中: ${itemsList.length} 個 / 全 ${Object.keys(ITEMS).length} 個`;
      }
    }

    if (itemSearchInput) {
      itemSearchInput.addEventListener("input", (e) => {
        itemSearchKeyword = e.target.value;
        renderItemsList();
      });
    }

    if (itemSortSelect) {
      itemSortSelect.addEventListener("change", (e) => {
        currentItemSort = e.target.value;
        renderItemsList();
      });
    }

    document.querySelectorAll(".item-cat-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".item-cat-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentItemCat = btn.getAttribute("data-cat");
        renderItemsList();
      });
    });

    // ステータスフィルターのチェックボックス＆全解除ボタンのイベント登録
    document.querySelectorAll(".stat-filter-chk").forEach(chk => {
      chk.addEventListener("change", () => {
        renderItemsList();
      });
    });

    const clearStatFiltersBtn = document.getElementById("clearStatFiltersBtn");
    if (clearStatFiltersBtn) {
      clearStatFiltersBtn.onclick = () => {
        document.querySelectorAll(".stat-filter-chk").forEach(chk => chk.checked = false);
        renderItemsList();
      };
    }

    // メインナビゲーションタブ切り替え
    const champControlsEl = document.getElementById("champControls");
    const viewChampsEl = document.getElementById("viewChampions");
    const viewItemsEl = document.getElementById("viewItems");
    const viewPicksEl = document.getElementById("viewPicks");

    // ユーザー提供のガレン対面表と、暫定の補足候補。勝率統計ではない。
    const pickRows = [["Akali", "Garen", "耐えて短期トレード", ["アカリ"]], ["Aatrox", "Garen", "Qの外側を避ける", ["アトロックス"]], ["Ambessa", "Garen", "ダッシュ後を狙う", ["アンベッサ"]], ["Illaoi", "Mordekaiser", "Eを避け、触手の位置を意識して戦う", ["イラオイ"]], ["Vladimir", "Garen", "序盤に圧力", ["ウラジミール"]], ["Olaf", "Garen", "R中の長期戦を避ける", ["オラフ"]], ["Cassiopeia", "Garen", "接近が難しいので慎重に", ["カシオペア"]], ["Galio", "Garen", "AP耐久型に物理ダメージ", ["ガリオ"]], ["Gangplank", "Garen", "樽の処理が重要", ["ガングプランク"]], ["Kled", "Garen", "乗馬中の長期戦を避ける", ["クレッド"]], ["Gwen", "Garen", "Q中央を回避", ["グウェン"]], ["Gragas", "Garen", "回復と妨害に注意", ["グラガス"]], ["Kayle", "Mordekaiser", "序盤に主導権。射程とRに注意", ["ケイル"]], ["Kennen", "Garen", "無理な接近を避ける", ["ケネン"]], ["KogMaw", "Garen", "珍しいTOP、序盤に圧力", ["コグ＝マウ"]], ["Zaahen", "Garen", "長期戦を避ける", ["ザーヘン"]], ["Singed", "Garen", "追いかけすぎない", ["シンジド"]], ["Swain", "Garen", "長期戦を避ける", ["スウェイン"]], ["Darius", "Garen", "不利ならBANを検討", ["ダリウス"]], ["Trundle", "Garen", "長い殴り合いを避ける", ["トランドル"]], ["Neeko", "Garen", "分身とEに注意", ["ニーコ"]], ["Heimerdinger", "Garen", "タレットに無理に突っ込まない", ["ヘイマーディンガー"]], ["Volibear", "Garen", "2回目のWを受けない", ["ボリベア"]], ["Rumble", "Garen", "長い炎上トレードを避ける", ["ランブル"]], ["Riven", "Garen", "短期トレードで対応", ["リヴェン"]], ["Lissandra", "Garen", "無理なダイブをしない", ["リサンドラ"]], ["Lillia", "Garen", "移動速度と継続ダメージに注意", ["リリア"]], ["Warwick", "Garen", "低HP時の回復に注意", ["ワーウィック"]], ["Malphite", "Mordekaiser", "対タンク枠。孤立Qを狙う", ["マルファイト"]], ["Ornn", "Mordekaiser", "タンク対策。鍛冶神の呼び声に注意", ["オーン"]], ["Sion", "Mordekaiser", "継続魔法ダメージ。Qの範囲から出る", ["サイオン"]], ["Chogath", "Mordekaiser", "タンク対策。QとRに注意", ["チョ＝ガス"]], ["TahmKench", "Mordekaiser", "長期戦と割合ダメージを意識", ["タム・ケンチ"]], ["Udyr", "Mordekaiser", "継続戦闘を意識", ["ウディア"]], ["KSante", "Mordekaiser", "AP継続ダメージを活用", ["カ・サンテ"]], ["Garen", "Mordekaiser", "長期戦で優位を狙う", ["ガレン"]], ["Shen", "Mordekaiser", "Rで相手のRによる離脱を妨害", ["シェン"]], ["Sett", "Mordekaiser", "W中央を回避", ["セト"]], ["Teemo", "Mordekaiser", "Qのブラインドを受けてもスキルで戦える", ["ティーモ"]], ["DrMundo", "Mordekaiser", "パッシブによる行動妨害への耐性に注意", ["ドクター・ムンド"]], ["Nasus", "Mordekaiser", "序盤にスタックを妨害", ["ナサス"]], ["Poppy", "Mordekaiser", "AP継続ダメージを活用", ["ポッピー"]], ["Yorick", "Mordekaiser", "メイデンとグールの処理に注意", ["ヨリック"]], ["Tryndamere", "Malphite", "通常攻撃対策。R中の殴り合いを避ける", ["トリンダメア"]], ["Yasuo", "Malphite", "対AD通常攻撃。Eの攻撃速度低下を活用", ["ヤスオ"]], ["Yone", "Malphite", "通常攻撃主体への候補。魔法ダメージとEの戻り位置に注意", ["ヨネ"]], ["Quinn", "Malphite", "対ADレンジ。R習得後に反撃", ["クイン"]], ["Vayne", "Malphite", "対ADレンジ。Wの確定ダメージに注意", ["ヴェイン"]], ["Jayce", "Malphite", "対ADレンジ。遠隔攻撃を受けすぎない", ["ジェイス"]], ["Urgot", "Malphite", "Eで攻撃速度を下げる", ["アーゴット"]], ["Ashe", "Malphite", "対ADレンジ", ["アッシュ"]], ["Jax", "Malphite", "Eの攻撃速度低下を活用。魔法ダメージに注意", ["ジャックス"]], ["Irelia", "Malphite", "攻撃速度低下を活用", ["イレリア"]], ["MonkeyKing", "Malphite", "物理ダメージ対策", ["ウーコン"]], ["Camille", "Malphite", "対ADだが確定ダメージに注意", ["カミール"]], ["JarvanIV", "Malphite", "対AD。防御低下に注意", ["ジャーヴァンIV"]], ["Gnar", "Malphite", "対ADレンジ。メガナーに注意", ["ナー"]], ["Nocturne", "Malphite", "対AD。スペルシールドに注意", ["ノクターン"]], ["Pantheon", "Malphite", "対AD。序盤は慎重に", ["パンテオン"]], ["Fiora", "Malphite", "Wと確定ダメージに注意", ["フィオラ"]], ["Briar", "Malphite", "通常攻撃主体。回復に注意", ["ブライアー"]], ["Renekton", "Malphite", "序盤のバーストを耐える", ["レネクトン"]], ["RekSai", "Malphite", "対AD。確定ダメージに注意", ["レク＝サイ"]], ["Mordekaiser", "Garen", "使い慣れたガレンで対応。長期戦を避け、短期トレードを意識", ["モルデカイザー"]]];
    let pickFilter = "すべて";
    function renderPickGuide() {
      const query = document.getElementById("pickSearch").value.trim().toLocaleLowerCase();
      const normalizedQuery = query === "アックス" ? "ジャックス" : query;
      const rows = pickRows.filter(row => (pickFilter === "すべて" || CHAMPIONS[row[1]]?.name === pickFilter) && [CHAMPIONS[row[0]]?.name, row[0], ...row[3]].some(name => matchSearch(name, normalizedQuery))).sort((a,b) => CHAMPIONS[a[0]].name.localeCompare(CHAMPIONS[b[0]].name, "ja"));
      document.getElementById("pickCount").textContent = rows.length + "対面を表示";
      const list = document.getElementById("pickList");
      list.replaceChildren();
      if (!rows.length) { list.textContent = "該当する対面はありません。未掲載の対面はガレンを基準に検討してください。"; return; }
      rows.forEach(row => {
        const card = document.createElement("div"); card.className = "pick-row";
        const title = document.createElement("strong"); title.textContent = CHAMPIONS[row[0]].name + " → ";
        const choice = document.createElement("span");
        const choiceClasses = { "ガレン": "garen", "モルデカイザー": "mordekaiser", "マルファイト": "malphite" };
        choice.className = "pick-choice-" + choiceClasses[CHAMPIONS[row[1]].name]; choice.textContent = CHAMPIONS[row[1]].name;
        title.append(choice);
        const reason = document.createElement("p"); reason.textContent = row[2];
        card.append(title, reason); list.append(card);
      });
    }
    document.getElementById("pickSearch").addEventListener("input", renderPickGuide);
    document.querySelectorAll("[data-pick]").forEach(button => button.addEventListener("click", () => {
      pickFilter = button.dataset.pick;
      document.querySelectorAll("[data-pick]").forEach(b => { b.classList.toggle("active", b === button); b.setAttribute("aria-pressed", String(b === button)); });
      renderPickGuide();
    }));
    renderPickGuide();

    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const target = tab.getAttribute("data-tab");
        viewPicksEl.style.display = target === "picks" ? "block" : "none";

        if (target === "champions") {
          viewChampsEl.style.display = "block";
          viewItemsEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "flex";
        } else if (target === "items") {
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "block";
          if (champControlsEl) champControlsEl.style.display = "none";
          renderItemsList();
        } else if (target === "picks") {
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "none";
        }
      });
    });

    // 検索入力イベント
    searchInput.addEventListener("input", (e) => {
      searchKeyword = e.target.value;
      renderList();
    });

    // ロールタブ切り替え
    document.querySelectorAll(".role-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".role-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentRole = btn.getAttribute("data-role");
        renderList();
      });
    });

    // 複合フィルターチップス (AAタイプ / ダメージ属性 / 特性)
    document.querySelectorAll("#champFilterBar .chip-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const filterType = btn.getAttribute("data-filter");
        const val = btn.getAttribute("data-val");

        if (btn.classList.contains("toggle-chip")) {
          // トグルボタン (複数選択可能)
          if (btn.classList.contains("active")) {
            btn.classList.remove("active");
            currentTraitFilters.delete(val);
          } else {
            btn.classList.add("active");
            currentTraitFilters.add(val);
          }
        } else {
          // 単一選択ボタングループ
          const parentGroup = btn.closest(".filter-group");
          if (parentGroup) {
            parentGroup.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("active"));
          }
          btn.classList.add("active");

          if (filterType === "attack") {
            currentAttackFilter = val;
          } else if (filterType === "damage") {
            currentDamageFilter = val;
          }
        }
        renderList();
      });
    });

    // フィルターリセットボタン
    const chipResetBtn = document.getElementById("chipResetBtn");
    if (chipResetBtn) {
      chipResetBtn.addEventListener("click", () => {
        currentAttackFilter = "ALL";
        currentDamageFilter = "ALL";
        currentTraitFilters.clear();
        document.querySelectorAll("#champFilterBar .chip-btn").forEach(btn => {
          if (btn.getAttribute("data-val") === "ALL") {
            btn.classList.add("active");
          } else {
            btn.classList.remove("active");
          }
        });
        renderList();
      });
    }

    // 初期レンダリング
    renderList();
    renderItemsList();

    // チャンピオン画像バックグラウンド・プリフェッチ（完全オフライン化）
    function prewarmChampionImages() {
      if (!('serviceWorker' in navigator) || !navigator.onLine || navigator.connection?.saveData || ['slow-2g','2g','3g'].includes(navigator.connection?.effectiveType)) return;
      const champList = Object.values(CHAMPIONS);
      let idx = 0;
      function fetchNextBatch() {
        if (idx >= champList.length || !navigator.onLine || navigator.connection?.saveData || ['slow-2g','2g','3g'].includes(navigator.connection?.effectiveType)) return;
        const end = Math.min(idx + 10, champList.length);
        for (let i = idx; i < end; i++) {
          const c = champList[i];
          const patch = c.patch || DEFAULT_PATCH;
          const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${patch}/img/champion/${c.id}.png`;
          const img = new Image();
          img.src = imgUrl;
        }
        idx = end;
        setTimeout(fetchNextBatch, 250);
      }
      setTimeout(fetchNextBatch, 1200);
    }
    prewarmChampionImages();

    // Service Worker 登録（更新チェック付き）
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js')
          .then(reg => {
            console.log('ServiceWorker registered:', reg.scope);
            reg.update();
          })
          .catch(err => console.log('ServiceWorker registration failed:', err));
      });
    }

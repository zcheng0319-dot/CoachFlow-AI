const chatStream = document.querySelector("#chatStream");
const chatForm = document.querySelector("#chatForm");
const questionInput = document.querySelector("#questionInput");

const demoAnswers = {
  starter: {
    question: "零基础适合从什么课程开始？",
    answer:
      "零基础建议先从兴趣和基本动作开始，不急着增加训练强度。结合当前班型，周末兴趣班更适合作为第一阶段，教练会从握拍、站位和正反手基础开始带练。",
  },
  course: {
    question: "周末兴趣班多少钱？还有名额吗？",
    answer:
      "周末兴趣班当前 Demo 价格为 1,600 元，周六 09:00 上课，由赵琳教练授课，目前显示剩余 9 个名额。课程信息可能变化，正式报名时建议再次确认。",
  },
  age: {
    question: "7 岁开始学乒乓球会不会太早？",
    answer:
      "7 岁可以开始系统启蒙。这个阶段更适合短时、多变化的练习，先培养球感、协调性和兴趣，每周保持规律训练比单次练很久更重要。",
  },
  level: {
    question: "孩子学过一年，算什么水平？",
    answer:
      "学习时间只能作为参考，还需要看正反手动作、连续对打、发球和步法。如果孩子能稳定完成基础对打，可以进一步了解基础强化班；如果动作仍不稳定，先巩固入门课程会更合适。",
  },
  advanced: {
    question: "周末基础强化班适合什么水平？",
    answer:
      "周末基础强化班适合已有基础、希望规范正反手和步法的 8–12 岁孩子。当前 Demo 班次为周日 14:00，李浩教练授课，价格 3,000 元，显示剩余 3 个名额。",
  },
};

function chooseAnswer(question, explicitKey) {
  if (explicitKey && demoAnswers[explicitKey]) return demoAnswers[explicitKey];

  if (/多少钱|名额|几点|周末兴趣班/.test(question)) return demoAnswers.course;
  if (/一年|水平|有基础/.test(question)) return demoAnswers.level;
  if (/7\s*岁|太早|启蒙年龄/.test(question)) return demoAnswers.age;
  if (/强化班|进阶/.test(question)) return demoAnswers.advanced;
  return {
    question,
    answer:
      "我可以根据孩子的年龄、学习经历、方便上课的时间和预算来匹配课程。您可以再告诉我这些信息，我会给出更具体的建议。",
  };
}

function createMessage(role, text, loading = false) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "AI";
    row.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = `message-bubble${role === "assistant" ? " answer" : ""}`;

  if (loading) {
    bubble.classList.add("typing");
    bubble.setAttribute("aria-label", "AI 正在思考");
    bubble.innerHTML = "<i></i><i></i><i></i>";
  } else {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
  }

  row.appendChild(bubble);
  return row;
}

function submitQuestion(question, answerKey) {
  const cleaned = question.trim();
  if (!cleaned) {
    questionInput.focus();
    return;
  }

  const demo = chooseAnswer(cleaned, answerKey);
  chatStream.appendChild(createMessage("user", cleaned));
  const typing = createMessage("assistant", "", true);
  chatStream.appendChild(typing);
  chatStream.scrollTop = chatStream.scrollHeight;
  questionInput.value = "";

  window.setTimeout(() => {
    typing.replaceWith(createMessage("assistant", demo.answer));
    chatStream.scrollTop = chatStream.scrollHeight;
  }, 420);
}

document.querySelectorAll("[data-demo]").forEach((button) => {
  button.addEventListener("click", () => {
    const demo = demoAnswers[button.dataset.demo];
    submitQuestion(demo.question, button.dataset.demo);
  });
});

document.querySelectorAll("[data-course-question]").forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.courseQuestion.includes("强化") ? "advanced" : "course";
    submitQuestion(button.dataset.courseQuestion, key);
  });
});

document.querySelectorAll("[data-focus-chat]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => questionInput.focus(), 300);
  });
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion(questionInput.value);
});

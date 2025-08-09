// Simple JavaScript file to greet user
function greetUser() {
  const name = prompt("What's your name?");
  if (name) {
    const message = `Hello, ${name}! 👋`;
    console.log(message);
    alert(message);
  } else {
    alert("You didn't enter a name.");
  }
}

// Call the function
greetUser();